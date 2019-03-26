import logging
import time
from io import BytesIO
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from PIL import Image

from flask import Flask, send_file

app = Flask(__name__)


@app.route("/")
def home():
    return "Nothing to see here."


@app.route("/api/<string:domain>/32.png")
def metaicon(domain):
    try:
        b = get_icon(domain)

        if b:
            b.seek(0)
            return send_file(b, mimetype="image/png")
    except Exception as e:
        logging.warn(e)

    return ("Not found", 404)


def get_icon(domain):
    start = time.time()
    logging.info(f"Getting content from {domain}")

    response = requests.get(
        f"http://{domain}",
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:65.0) Gecko/20100101 Firefox/65.0"
        },
    )
    html = BeautifulSoup(response.content, features="html.parser")

    logging.info(f"Content received {time.time() - start}")
    icons = [
        icon
        for icon in html.find_all("link")
        if any([x in [y.lower() for y in icon.attrs.get("rel", [])] for x in ["icon"]])
    ]
    logging.info(f"{icons} {time.time() - start}")

    if not icons:
        favicon_url = urljoin(response.url, "favicon.ico")
        logging.info(f"Defaulting to favicon url {favicon_url} {time.time() - start}")
        r = requests.get(favicon_url)

        if r.status_code != 200:
            return
    else:
        icon_url = icons[0].attrs["href"]
        if "://" not in icon_url:
            icon_url = urljoin(response.url, icon_url)

        logging.info(f"{icon_url} {time.time() - start}")
        r = requests.get(icon_url)

    i = Image.open(BytesIO(r.content))
    i = i.resize((32, 32), resample=Image.BICUBIC)

    logging.info(f"{i.size} {time.time() - start}")

    b = BytesIO()
    i.save(b, "PNG")

    logging.info(f"Done {time.time() - start}")
    return b


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    get_icon("ipinfo.io")
