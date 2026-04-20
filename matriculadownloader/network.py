import json
import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .app_constants import HEADERS, REQ_TIMEOUT
from .metadata_parser import (
    enrich_matricula_metadata,
    extract_book_title,
    extract_matricula_image_urls,
    extract_matricula_metadata,
    extract_page_metadata,
)
from .text_utils import safe_name


def fetch_html(url: str, session: requests.Session | None = None) -> tuple[str, BeautifulSoup]:
    req = session or requests
    response = req.get(url, headers=HEADERS, timeout=REQ_TIMEOUT)
    response.raise_for_status()
    html_text = response.text
    return html_text, BeautifulSoup(html_text, 'html.parser')


def _extract_netx_asset_id(book_url: str) -> int | None:
    for pattern in (r'#asset/(\d+)', r'/asset/(\d+)'):
        match = re.search(pattern, book_url)
        if match:
            return int(match.group(1))
    return None


def _extract_netx_document_id(book_url: str) -> int | None:
    for pattern in (r'#document/(\d+)', r'/document/(\d+)'):
        match = re.search(pattern, book_url)
        if match:
            return int(match.group(1))
    return None


def _netx_base_url(book_url: str) -> str:
    parsed = urlparse(book_url)
    return f'{parsed.scheme}://{parsed.netloc}'


def _netx_portal_context(book_url: str) -> tuple[str, str]:
    parsed = urlparse(book_url)
    parts = [p for p in parsed.path.split('/') if p]
    portal_context = '/portals'
    landing_url = f'{parsed.scheme}://{parsed.netloc}/portals/'
    if len(parts) >= 2 and parts[0] == 'portals':
        portal_context = f'/portals/{parts[1]}'
        landing_url = f'{parsed.scheme}://{parsed.netloc}{portal_context}/'
    return portal_context, landing_url


def _netx_collect_from_browser(book_url: str) -> tuple[requests.Session, str, str, list[str], str]:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            'NetX support requires selenium and webdriver-manager. '
            'Please install them with: pip install selenium webdriver-manager'
        ) from exc

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1800,1400')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get(book_url)
        deadline = time.time() + 35
        session_key = ''
        preview_urls: list[str] = []
        page_source = ''
        title = ''
        while time.time() < deadline:
            try:
                page_source = driver.page_source or ''
                title = driver.title or ''
            except Exception:
                pass

            for cookie in driver.get_cookies():
                if cookie.get('name') == 'sessionKey' and cookie.get('value'):
                    session_key = cookie['value']

            try:
                srcs = driver.execute_script("""
                    const vals = new Set();
                    document.querySelectorAll('img, source').forEach(el => {
                        if (el.src) vals.add(el.src);
                        const ds = el.getAttribute('data-src');
                        if (ds) vals.add(ds);
                    });
                    document.querySelectorAll('a').forEach(el => { if (el.href) vals.add(el.href); });
                    return Array.from(vals);
                """) or []
                for u in srcs:
                    if isinstance(u, str) and '/api/file/asset/' in u and '/preview' in u:
                        preview_urls.append(u)
            except Exception:
                pass

            try:
                logs = driver.get_log('performance')
                for entry in logs:
                    msg = json.loads(entry['message'])['message']
                    params = msg.get('params', {})
                    req = params.get('request', {})
                    resp = params.get('response', {})
                    url = req.get('url') or resp.get('url') or ''
                    if isinstance(url, str) and '/api/file/asset/' in url and '/preview' in url:
                        preview_urls.append(url)
            except Exception:
                pass

            if session_key and preview_urls:
                break
            time.sleep(1.0)

        if not session_key:
            raise RuntimeError('Could not obtain NetX sessionKey cookie from the portal.')

        sess = requests.Session()
        sess.headers.update(HEADERS)
        parsed = urlparse(book_url)
        domain = parsed.netloc
        portal_context, landing_url = _netx_portal_context(book_url)

        sess.cookies.set('sessionKey', session_key, domain=domain, path='/')
        sess.cookies.set('portalContext', portal_context, domain=domain, path='/')
        for cookie in driver.get_cookies():
            if cookie.get('value'):
                sess.cookies.set(cookie['name'], cookie['value'], domain=domain, path=cookie.get('path') or '/')
        try:
            sess.get(landing_url, timeout=REQ_TIMEOUT)
        except Exception:
            pass
        return sess, session_key, page_source, sorted(set(preview_urls)), title
    finally:
        driver.quit()


def _netx_rpc(session: requests.Session, base_url: str, method: str, params: list, rpc_id: str = '1'):
    payload = {
        'dataContext': 'json',
        'jsonrpc': '2.0',
        'method': method,
        'id': rpc_id,
        'params': params,
    }
    response = session.post(f'{base_url}/x7/v1.2/json/{method}', json=payload, timeout=REQ_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if 'error' in data and data['error']:
        raise RuntimeError(f'NetX API error for {method}: {data["error"]}')
    return data.get('result')


def _netx_meta_from_asset(asset_obj: dict) -> dict:
    names = asset_obj.get('attributeNames') or []
    values = asset_obj.get('attributeValues') or []
    mapping = {str(name): value for name, value in zip(names, values)}

    title = (
        mapping.get('BAE KB Titel')
        or mapping.get('Titel des Dokuments')
        or mapping.get('Titel')
        or mapping.get('Dokumentname')
        or mapping.get('Datensatzname')
        or mapping.get('Objekttitel')
        or asset_obj.get('name')
        or f"Asset {asset_obj.get('assetId', '')}"
    )
    daterange = mapping.get('Laufzeit') or mapping.get('Jahr') or mapping.get('Datum') or ''
    ort = mapping.get('Pfarrei') or mapping.get('Ort') or mapping.get('Stadt') or asset_obj.get('name') or 'Unbekannt'
    stadtteil = mapping.get('Stadtteil') or ''
    if stadtteil and stadtteil not in str(ort):
        ort = f'{ort} - {stadtteil}'
    buchtyp = mapping.get('Art des Kirchenbuches') or mapping.get('Buchtyp') or ''

    return {
        'ort': str(ort).strip(),
        'title': str(title).strip(),
        'daterange': str(daterange).strip(),
        'buchtyp': str(buchtyp).strip(),
    }


def _netx_ids_from_text(text: str) -> list[int]:
    ids: list[int] = []
    patterns = [
        r'/api/file/asset/(\d+)/preview',
        r'"assetId"\s*:\s*(\d+)',
        r'"constituentIds"\s*:\s*\[(.*?)\]',
        r'#asset/(\d+)',
        r'/asset/(\d+)',
        r"data-asset-id=[\"'](\d+)[\"']",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.S):
            if pat == r'"constituentIds"\s*:\s*\[(.*?)\]':
                chunk = m.group(1)
                ids.extend(int(x) for x in re.findall(r'\d+', chunk))
            else:
                ids.append(int(m.group(1)))
    out=[]; seen=set()
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _netx_build_preview_urls(base_url: str, ids: list[int]) -> list[str]:
    return [f'{base_url}/api/file/asset/{i}/preview' for i in ids]


def _netx_title_from_html(html: str, fallback: str = '') -> str:
    m = re.search(r'<title>(.*?)</title>', html, re.I | re.S)
    if m:
        title = re.sub(r'\s+', ' ', BeautifulSoup(m.group(1), 'html.parser').get_text(' ', strip=True)).strip()
        if title:
            return title
    return fallback


def _extract_netx_urls(book_url: str):
    base_url = _netx_base_url(book_url)
    asset_id = _extract_netx_asset_id(book_url)
    document_id = _extract_netx_document_id(book_url)

    session, session_key, page_source, browser_preview_urls, browser_title = _netx_collect_from_browser(book_url)

    preview_urls: list[str] = list(browser_preview_urls)
    meta = {'ort': 'Bistum Essen', 'title': '', 'daterange': '', 'buchtyp': ''}

    if asset_id:
        try:
            asset_objects = _netx_rpc(session, base_url, 'getAssetObjects', [session_key, [asset_id]], rpc_id='netx-asset')
            if asset_objects:
                asset_obj = asset_objects[0]
                meta.update({k: v for k, v in _netx_meta_from_asset(asset_obj).items() if v})
                constituent_ids = asset_obj.get('constituentIds') or []
                if constituent_ids:
                    preview_urls = _netx_build_preview_urls(base_url, constituent_ids)
                elif not preview_urls:
                    preview_url = asset_obj.get('previewUrl') or f'/api/file/asset/{asset_id}/preview'
                    if not str(preview_url).startswith('http'):
                        preview_url = f'{base_url}{preview_url}'
                    preview_urls = [preview_url]
        except Exception:
            pass

    if document_id and not preview_urls:
        ids = _netx_ids_from_text(page_source)
        if ids:
            preview_urls = _netx_build_preview_urls(base_url, ids)

    if document_id:
        ids = _netx_ids_from_text(page_source)
        if ids and len(ids) > len(preview_urls):
            preview_urls = _netx_build_preview_urls(base_url, ids)

    if not preview_urls:
        preview_urls = [u if u.startswith('http') else f'{base_url}{u}' for u in re.findall(r'(/api/file/asset/\d+/preview)', page_source)]

    if not meta.get('title'):
        title = _netx_title_from_html(page_source, browser_title)
        title = re.sub(r'\b(NetX|Bistum Essen|Archive?)\b', '', title, flags=re.I).strip(' |-')
        meta['title'] = title or (f'Dokument {document_id}' if document_id else f'Asset {asset_id}' if asset_id else 'NetX Dokument')

    if meta.get('title') and not meta.get('buchtyp'):
        low = meta['title'].lower()
        for word in ('Taufen','Trauungen','Beerdigungen','Sterbefälle','Geburten','Firmungen','Heiraten'):
            if word.lower() in low:
                meta['buchtyp'] = word
                break

    folder_title = meta.get('title') or (f'Dokument {document_id}' if document_id else 'NetX Dokument')
    if meta.get('daterange'):
        folder_title = f"{folder_title} {meta['daterange']}"
    folder_name = safe_name(folder_title)

    def sort_key(u: str):
        m = re.search(r'/asset/(\d+)/preview', u)
        return int(m.group(1)) if m else 10**18
    preview_urls = sorted(dict.fromkeys(preview_urls), key=sort_key)
    return preview_urls, folder_name, meta


def extract_image_urls(book_url: str):
    try:
        urls: list[str] = []
        folder_name = 'Unbekannt'
        image_urls: list[str] = []

        if 'netx.bistum-essen.de' in book_url and '/portals' in book_url:
            return _extract_netx_urls(book_url)

        html_text, soup = fetch_html(book_url)
        meta = extract_page_metadata(soup, html_text, book_url)

        if 'dfg-viewer.de' in book_url:
            if 'tx_dlf[page]' not in book_url:
                sep = '&' if '?' in book_url else '?'
                book_url = f'{book_url}{sep}tx_dlf[page]=1'
            html, soup = fetch_html(book_url)
            title_dd = soup.select_one('dd.tx-dlf-title')
            title = title_dd.get_text(strip=True) if title_dd else 'Unbekannt'
            ctx_dds = soup.select('dl.tx-dlf-metadata-titledata dd')
            bestand_raw = ctx_dds[1].get_text(strip=True) if len(ctx_dds) >= 2 else ''
            m_bestand = re.search(r'Bestand:\s*(.+)', bestand_raw)
            bestand_full = m_bestand.group(1).strip() if m_bestand else ''
            ort_raw = bestand_full.split(' - ')[0]
            ort_parts = ort_raw.split(' ', 1)
            ort = ort_parts[1].strip() if len(ort_parts) > 1 else ort_raw.strip()
            m_years = re.search(r'(\d{4})\D+(\d{4})', bestand_full)
            years = f'{m_years.group(1)}-{m_years.group(2)}' if m_years else ''
            meta = {'title': title.strip(), 'ort': ort, 'daterange': years}
            folder_name = safe_name(f'{title} {years}') if years else safe_name(title)
            options = soup.select("select[name='tx_dlf[page]'] option")
            total_pages = len(options) if options else 1
            match = re.search(r'tx_dlf_viewer\s*=\s*new dlfViewer\([^)]*?images\s*:\s*\[\s*\{\s*"url"\s*:\s*"([^"]+)"', html, re.DOTALL)
            if not match:
                return [], folder_name, meta
            first_url = match.group(1).replace('\\/', '/')
            base_url, filename = first_url.rsplit('/', 1)
            m2 = re.match(r'(.+_)(\d{4})_(\d{4})_(\d{3}\.jpg)', filename)
            if not m2:
                return [first_url], folder_name, meta
            prefix, _first_page, fix_mid, tail = m2.groups()
            urls = [f'{base_url}/{prefix}{i:04d}_{fix_mid}_{tail}' for i in range(1, total_pages + 1)]
            return urls, folder_name, meta

        if 'matricula-online.eu' in book_url:
            meta.update({k: v for k, v in extract_matricula_metadata(html_text).items() if v})
            meta = enrich_matricula_metadata(soup, html_text, meta)
            if not meta.get('title'):
                meta['title'] = extract_book_title(soup, book_url)
            folder_name = safe_name(meta.get('ort', meta['title']))
            return extract_matricula_image_urls(soup, html_text), folder_name, meta

        if 'findbuch.net' in book_url:
            possible = re.findall(r'/a_pics/ks/[^\"\']+\.jpg', html_text)
            for p in possible:
                full = f'https://www.findbuch.net{p}'
                if full not in image_urls:
                    image_urls.append(full)
            if not image_urls:
                onclick_links = re.findall(r'javascript:m_click\(\d+\)', html_text)
                if onclick_links:
                    base_guess = re.search(r'(/a_pics/ks/[^\s"]+_)\d{3}\.jpg', html_text)
                    if base_guess:
                        base_url = 'https://www.findbuch.net' + base_guess.group(1)
                        indices = [int(x.split('(')[1].split(')')[0]) for x in onclick_links]
                        for index in indices:
                            image_urls.append(base_url + f'{index + 3:03d}.jpg')
            return sorted(set(image_urls)), extract_book_title(soup, book_url), meta

        if 'archiviodiocesanoreggiobova.it' in book_url:
            page_text = soup.get_text('\n', strip=True)
            def get_field(label: str) -> str:
                match = re.search(rf'{label}:\s*([^\n]+)', page_text, re.I)
                return match.group(1).strip() if match else ''
            file_code = get_field('File') or 'page'
            parish = get_field('Parish') or 'Unbekannt'
            typology = get_field('Typology') or 'Unbekannt'
            period = get_field('Period') or ''
            m_total = re.search(r'Image\s+\d+\s+of\s+(\d+)', page_text, re.I)
            total_pages = int(m_total.group(1)) if m_total else 1
            m_album = re.search(r'/photo_details/(\d+)/', book_url)
            album_id = m_album.group(1) if m_album else 'unknown'
            match = re.match(r'(.+?)(\d{3})$', file_code)
            if not match:
                return [], safe_name(parish), {'ort': parish, 'title': typology, 'daterange': period}
            prefix, _first_page = match.groups()
            base_img_url = f'https://www.archiviodiocesanoreggiobova.it/wp-content/uploads/wp_photo_seller/{album_id}'
            urls = [f'{base_img_url}/watermark_{prefix}{i:03d}.jpg' for i in range(1, total_pages + 1)]
            meta = {'ort': parish, 'title': typology, 'daterange': period}
            folder_name = safe_name(f'{typology} {period}'.strip() or typology)
            return urls, folder_name, meta

        return urls, folder_name, meta
    except Exception:
        return [], 'Unbekanntes_Buch', {}


def download_binary(url: str, target_path: str) -> None:
    response = requests.get(url, headers=HEADERS, stream=True, timeout=30)
    response.raise_for_status()
    with open(target_path, 'wb') as handle:
        for chunk in response.iter_content(65536):
            handle.write(chunk)
