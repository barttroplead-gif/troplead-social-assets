"""Publish one planned post to Instagram @trop_lead.

Usage: python3 publish.py 2026-w44 p1
Images are served from this repo via raw.githubusercontent.com; the Graph API
token is injected by the session proxy.
"""
import json
import sys
import time
import urllib.parse
import urllib.request

IG_USER = "17841428078997838"
API = "https://graph.facebook.com/v21.0"
RAW = "https://raw.githubusercontent.com/barttroplead-gif/troplead-social-assets/main"


def call(method, path, **params):
    data = urllib.parse.urlencode(params).encode() if method == "POST" else None
    url = f"{API}/{path}" + ("" if data else "?" + urllib.parse.urlencode(params))
    with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method)) as r:
        return json.load(r)


def wait_ready(container_id):
    for _ in range(30):
        status = call("GET", container_id, fields="status_code")["status_code"]
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"container {container_id} failed")
        time.sleep(5)
    raise TimeoutError(container_id)


def main(week, key):
    post = json.load(open(f"{week}/posts.json"))[key]
    urls = [f"{RAW}/{week}/{img}" for img in post["images"]]
    if len(urls) == 1:
        container = call("POST", f"{IG_USER}/media", image_url=urls[0], caption=post["caption"])["id"]
    else:
        children = [call("POST", f"{IG_USER}/media", image_url=u, is_carousel_item="true")["id"] for u in urls]
        for c in children:
            wait_ready(c)
        container = call("POST", f"{IG_USER}/media", media_type="CAROUSEL", children=",".join(children),
                         caption=post["caption"])["id"]
    wait_ready(container)
    media_id = call("POST", f"{IG_USER}/media_publish", creation_id=container)["id"]
    print(call("GET", media_id, fields="permalink,timestamp"))


if __name__ == "__main__":
    main(*sys.argv[1:3])
