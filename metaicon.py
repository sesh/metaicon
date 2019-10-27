import base64
import logging
import json
import re
import time
import sys
import hashlib

from io import BytesIO
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from PIL import Image, ImageDraw

from flask import Flask, send_file

from popular.icons import POPULAR_ICONS


app = Flask(__name__)

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

def get(url):
    return requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:65.0) Gecko/20100101 Firefox/65.0"
        },
        timeout=2,
    )

@app.route("/")
def home():
    return "Nothing to see here."


@app.route("/api/<string:domain>/32.png")
def metaicon(domain):
    if not is_valid_hostname(domain):
        logging.info(f"Request for invalid hostname: {domain}")
        return ("Invalid hostname", 400)

    try:
        b = get_popular_icon(domain)

        if not b:
            b = get_icon(domain)

        if b:
            b.seek(0)
            return send_file(b, mimetype="image/png")
    except Exception as e:
        logging.warn(e)
        b = get_default_image(domain)
        return send_file(b, mimetype="image/png")


def get_default_image(domain):
    logging.info('Using "default" image for', domain)
    m = hashlib.sha256()
    m.update(domain.encode())
    colour = m.hexdigest()[:6]

    i = Image.new('RGB', (32, 32))
    d = ImageDraw.Draw(i)
    d.rectangle([0, 0, 32, 32], f'#{colour}', f'#{colour}')

    b = BytesIO()
    i.save(b, "PNG")
    b.seek(0)
    return b

def get_popular_icon(domain):
    result = POPULAR_ICONS.get(domain)

    if not result:
        result = POPULAR_ICONS.get('www.' + domain)

    if result:
        logging.info(f'Cache hit for domain: {domain}')
        return BytesIO(base64.b64decode(result))


def get_icon(domain):
    start = time.time()
    logging.info(f"Getting content from {domain}")

    try:
        response = get(f"https://{domain}")
    except:
        get(f"http://{domain}")

    html = BeautifulSoup(response.content, features="html.parser")
    logging.info(f"Content received {time.time() - start}")

    icons = []
    for icon in html.find_all("link"):
        rel = icon.attrs.get("rel", [])
        rel = [x.lower() for x in rel]

        if any([x in rel for x in ["icon", "apple-touch-icon"]]):
            href = icon.attrs.get("href")
            if not href or href.endswith(".svg"):
                continue
            icons.append(icon)

    if not icons:
        favicon_url = urljoin(response.url, "favicon.ico")
        logging.info(f"Defaulting to favicon url {favicon_url} {time.time() - start}")
        r = get(favicon_url)

        if r.status_code != 200:
            return
    else:
        icon_url = icons[0].attrs["href"]
        if "://" not in icon_url:
            icon_url = urljoin(response.url, icon_url)

        logging.info(f"{icon_url} {time.time() - start}")
        r = get(icon_url)

    i = Image.open(BytesIO(r.content))
    i = i.resize((32, 32), resample=Image.BICUBIC)

    logging.info(f"{i.size} {time.time() - start}")

    b = BytesIO()
    i.save(b, "PNG")

    logging.info(f"Done {time.time() - start}")
    return b


def is_valid_hostname(hostname):
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1]  # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))
