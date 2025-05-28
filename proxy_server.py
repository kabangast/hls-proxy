from flask import Flask, request, Response, make_response
import requests
from urllib.parse import quote, urljoin
import re

app = Flask(__name__)

HEADERS = {
    'Referer': 'https://play.ezyproxy.xyz/',
    'Origin': 'https://play.ezyproxy.xyz',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
}

TOKEN = "xAXD9RCV"

@app.route('/proxy.m3u8')
@app.route('/proxy')
def proxy_playlist():
    original_url = request.args.get("url")
    if not original_url:
        return "Missing 'url' parameter", 400

    r = requests.get(original_url, headers=HEADERS)
    if r.status_code != 200:
        return f"Failed to fetch playlist ({r.status_code})", 502

    base_url = original_url.rsplit('/', 1)[0] + '/'
    server_url = request.host_url.rstrip('/')

    lines = []
    for line in r.text.splitlines():
        if line.startswith("#EXT-X-KEY"):
            key_match = re.search(r'URI="([^"]+)"', line)
            if key_match:
                key_uri = key_match.group(1)
                sep = '&' if '?' in key_uri else '?'
                key_uri += f"{sep}token={TOKEN}"
                proxy_key_url = f"{server_url}/key?url={quote(key_uri, safe='')}"
                line = re.sub(r'URI="[^"]+"', f'URI="{proxy_key_url}"', line)
        elif line and not line.startswith("#"):
            ts_url = urljoin(base_url, line)
            proxy_ts_url = f"{server_url}/ts?url={quote(ts_url, safe='')}"
            line = proxy_ts_url
        lines.append(line)

    modified_playlist = "\n".join(lines)

    response = make_response(modified_playlist)
    response.headers["Content-Type"] = "application/x-mpegURL"
    response.headers["Content-Disposition"] = 'inline; filename="playlist.m3u8"'
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.route('/key')
def proxy_key():
    key_url = request.args.get("url")
    if not key_url:
        return "Missing 'url' parameter", 400

    r = requests.get(key_url, headers=HEADERS)
    if r.status_code != 200:
        return f"Failed to fetch key ({r.status_code})", 502

    response = Response(r.content, content_type='application/octet-stream')
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.route('/ts')
def proxy_ts():
    ts_url = request.args.get("url")
    if not ts_url:
        return "Missing 'url' parameter", 400

    r = requests.get(ts_url, headers=HEADERS, stream=True)
    if r.status_code != 200:
        return f"Failed to fetch TS segment ({r.status_code})", 502

    def generate():
        for chunk in r.iter_content(chunk_size=8192):
            yield chunk

    response = Response(generate(), content_type='video/MP2T')
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
