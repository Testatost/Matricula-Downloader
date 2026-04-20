import base64
import re
from bs4 import BeautifulSoup
from .text_utils import safe_name


def extract_book_title(soup: BeautifulSoup, url: str) -> str:
    title = None
    h2 = soup.find('h2')
    if h2 and h2.text.strip():
        title = h2.text.strip()

    if not title and 'findbuch.net' in url:
        h1 = soup.find('h1')
        if h1 and h1.text.strip():
            title = h1.text.strip()
        else:
            td = soup.find('td', class_='text2')
            if td and td.text.strip():
                title = td.text.strip()

    if not title and soup.title and soup.title.text.strip():
        title = soup.title.text.strip()

    if not title:
        parts = [part for part in url.split('/') if part]
        title = parts[-1] if parts else 'Unbekanntes_Buch'

    return safe_name(title)


def extract_page_metadata(soup: BeautifulSoup, html_text: str, book_url: str) -> dict:
    meta: dict[str, str] = {}
    label_map = {
        'Signatur': 'signatur',
        'Bestand': 'bestand',
        'Datierung': 'daterange',
        'Titel': 'title',
        'Edition': 'edition',
        'Ersteller': 'creator',
        'Bemerkung': 'remark',
    }

    for tr in soup.find_all('tr'):
        cells = tr.find_all(['td', 'th'])
        if len(cells) < 2:
            continue
        label_text = cells[0].get_text(strip=True).rstrip(':')
        value_text = cells[1].get_text(strip=True)
        if label_text in label_map and value_text:
            meta[label_map[label_text]] = value_text

    if 'kirchenbücher-südtirol' in book_url:
        ort = None
        bestand = meta.get('bestand', '')
        match = re.search(r'KB_([A-Z_]+)', bestand)
        if match:
            tokens = match.group(1).split('_')
            if tokens:
                ort = tokens[-1].title()
        if not ort:
            match = re.search(r'~KB_([A-Z_]+)\._~', html_text)
            if match:
                tokens = match.group(1).split('_')
                if tokens:
                    ort = tokens[-1].title()
        if ort:
            meta['ort'] = ort

    return meta


def enrich_matricula_metadata(soup: BeautifulSoup, html_text: str, meta: dict) -> dict:
    label = soup.find(string=re.compile(r'Pfarre/Ort'))
    if label:
        parent = label.parent
        link = parent.find_next('a')
        if link and link.get_text(strip=True):
            meta.setdefault('ort', link.get_text(strip=True))
        else:
            text = parent.get_text(' ', strip=True)
            match = re.search(r'Pfarre/Ort\s+(.+)', text)
            if match and match.group(1).strip():
                meta.setdefault('ort', match.group(1).strip())

    sig_label = soup.find(string=re.compile(r'Signatur'))
    if sig_label:
        text = sig_label.parent.get_text(' ', strip=True)
        match = re.search(r'Signatur\s+([A-Z0-9+ ]+)', text)
        if match:
            meta.setdefault('signatur', match.group(1).strip())

    bt_label = soup.find(string=re.compile(r'Buchtyp'))
    if bt_label:
        text = bt_label.parent.get_text(' ', strip=True)
        match = re.search(r'Buchtyp\s+(.+)', text)
        if match:
            meta.setdefault('buchtyp', match.group(1).strip())

    if 'title' not in meta and (meta.get('buchtyp') or meta.get('signatur')):
        meta['title'] = f"{meta.get('buchtyp', '')} {meta.get('signatur', '')}".strip()

    if not meta.get('daterange'):
        match = re.search(r'(\d{4}).{0,40}(\d{4})', html_text, re.DOTALL)
        if match:
            meta['daterange'] = f"{match.group(1)}-{match.group(2)}"

    return meta


def extract_matricula_metadata(html_text: str) -> dict:
    meta: dict[str, str] = {}

    m_ort = re.search(r'<th>Pfarre/Ort</th><td><a [^>]*>([^<]+)</a>', html_text)
    if not m_ort:
        m_ort = re.search(r'<li class="breadcrumb-item"><a [^>]*>/[^>]*/([^<]+)/</a>', html_text)
    if not m_ort:
        m_ort = re.search(r'<title>[^|]*\|\s*([^|]+)\s*\|', html_text)
    if m_ort:
        meta['ort'] = m_ort.group(1).strip()

    m_title = re.search(r'<li class="breadcrumb-item active">\s*([^<]+?)\s*\|', html_text)
    if not m_title:
        m_title = re.search(r'<th>Buchtyp</th><td>([^<]+)</td>', html_text)
    if not m_title:
        m_title = re.search(r'<title>([^|]+?)\|', html_text)
    if not m_title:
        m_json = re.search(r'MatriculaDocView\.init\(\{(.*?)\}\)', html_text, re.DOTALL)
        if m_json:
            m_desc = re.search(r'"description"\s*:\s*"([^"]+)"', m_json.group(1))
            m_book = re.search(r'"book"\s*:\s*"([^"]+)"', m_json.group(1))
            if m_desc:
                title_str = m_desc.group(1)
                if m_book:
                    title_str += ' ' + m_book.group(1)
                meta['title'] = title_str
    if m_title:
        meta['title'] = m_title.group(1).strip()

    m_date = re.search(r'<th>Datum von</th><td>([^<]+)</td>.*?<th>Datum bis</th><td>([^<]+)</td>', html_text, re.DOTALL)
    if m_date:
        y1 = re.search(r'(\d{4})', m_date.group(1).strip())
        y2 = re.search(r'(\d{4})', m_date.group(2).strip())
        if y1 and y2:
            meta['daterange'] = f"{y1.group(1)}–{y2.group(1)}"

    return meta


def extract_matricula_image_urls(soup: BeautifulSoup, html_text: str) -> list[str]:
    image_urls: list[str] = []
    if 'MatriculaDocView' not in html_text:
        return image_urls

    for tag in soup.find_all('script'):
        text = tag.string or tag.text
        if not text or '"files": [' not in text:
            continue
        match = re.search(r'"files":\s*(\[[^\]]+\])', text)
        if not match:
            continue
        raw_list = match.group(1)
        encoded = re.findall(r'"(/image/[^"]+)"', raw_list)
        for encoded_fragment in encoded:
            b64 = encoded_fragment.split('/image/')[-1].strip('/')
            try:
                missing = len(b64) % 4
                if missing:
                    b64 += '=' * (4 - missing)
                decoded = base64.b64decode(b64).decode('utf-8')
                if decoded.startswith('http'):
                    image_urls.append(decoded)
                else:
                    image_urls.append('https://img.data.matricula-online.eu' + decoded)
            except Exception:
                continue
    return sorted(set(image_urls))
