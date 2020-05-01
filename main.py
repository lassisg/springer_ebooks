import os
import re
import pandas as pd
import requests as req
from tqdm import tqdm
from bs4 import BeautifulSoup


def get_data(url: str):
    r = req.get(url)
    download_link = ''
    file_name = ''
    subtitle = ''
    if r.ok:
        soup = BeautifulSoup(r.text, 'html.parser')
        try:
            download_link = soup.find('a',
                                      class_="test-bookpdf-link").get('href')
        except AttributeError as NoLinkError:
            print(NoLinkError)
        finally:
            title_tag = soup.h1
            subtitle_tag = soup.find('h2', class_="page-title__subtitle")

            title = name_prep(title_tag.string) if title_tag.string else ''
            if subtitle_tag:
                subtitle = f"-{name_prep(subtitle_tag.string)}"
            file_name = f"{title}{subtitle}.pdf" if title else ''

    else:
        print(r.status_code)

    return download_link, file_name


def name_prep(file_name: str) -> str:
    name = re.sub('[<>\\|?*]', "", file_name)
    name = re.sub(': ', "-", name)
    name = re.sub('[:/]', "-", name)
    name = name.replace(' ', '_')
    return name


base_url = 'http://link.springer.com'
book_list = pd.read_excel('Springer_Ebooks.xlsx')
book_list["Edition"] = book_list["Edition"].astype(str)
save_folder = os.path.join(os.path.curdir, 'pdf')
pd_error = pd.DataFrame()

for index, book in book_list.iterrows():
    year = str(book.Edition)
    if len(book.Edition) > 4:
        year = book.Edition.split()[-1]

    download_url, file_name = get_data(book.OpenURL)
    if not download_url:
        pd_error = pd_error.append(book)
        continue

    if not file_name:
        file_name = f"{name_prep(book.Title)}.pdf"

    file_name = f"{year}-{file_name}"

    response = req.get(f'{base_url}{download_url}',
                       allow_redirects=True, stream=True)
    file_size = int(response.headers.get('Content-Length', 0))

    chunk_size = 1024
    progress = tqdm(response.iter_content(chunk_size),
                    f"Downloading {file_name}",
                    total=file_size,
                    unit="KB",
                    unit_scale=True,
                    unit_divisor=chunk_size)

    with open(os.path.join(save_folder, file_name), "wb") as f:
        for data in progress:
            progress.update(len(data))
            f.write(data)

pd_error.index = pd_error.index + 2
pd_error.to_excel("error_list.xlsx")
