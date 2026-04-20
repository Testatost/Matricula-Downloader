import os
from PIL import Image


def create_pdf_from_folder(folder: str, save_path: str) -> None:
    images = sorted(
        os.path.join(folder, name)
        for name in os.listdir(folder)
        if name.lower().endswith('.jpg')
    )
    if not images:
        raise FileNotFoundError('Keine JPG-Dateien im Ordner gefunden.')
    first = Image.open(images[0]).convert('RGB')
    rest = [Image.open(path).convert('RGB') for path in images[1:]]
    first.save(save_path, save_all=True, append_images=rest)
