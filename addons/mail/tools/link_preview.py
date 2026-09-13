import logging
import re
import time
from typing import Any, Literal

import chardet
import requests
from lxml import html
from urllib3.exceptions import LocationParseError

from odoo.libs.debug_log import DebugLog
from odoo.libs.guarded_http import GuardedAdapter, RefusedDestination

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

MAX_HEAD_BYTES = 512 * 1024
MAX_REDIRECTS = 5
MAX_FETCH_SECONDS = 10
HEAD_SCAN_CHUNK_SIZE = 8192


def get_link_preview_session(env: Any) -> requests.Session:
    return env["ir.egress"].session(
        purpose="link_preview",
        max_bytes=None,
        max_seconds=MAX_FETCH_SECONDS,
        max_redirects=MAX_REDIRECTS,
    )


def get_link_preview_from_url(
    url: str, request_session: requests.Session
) -> dict[str, Any] | Literal[False]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
        "Odoo-Link-Preview": "True",
    }
    deadline = time.monotonic() + MAX_FETCH_SECONDS
    try:
        adapter = request_session.get_adapter(url)
    except requests.exceptions.InvalidSchema:
        _debug.logic("preview_failed", error="InvalidSchema")
        return False
    if not isinstance(adapter, GuardedAdapter):
        msg = "a link preview fetches through ir.egress: use get_link_preview_session"
        raise TypeError(msg)
    try:
        with _debug.perf("preview_fetched") as span:
            response = request_session.get(url, timeout=3, headers=headers, stream=True)
            span.set(status=getattr(response, "status_code", None))
    except RefusedDestination as refusal:
        _debug.logic("preview_aborted", reason="refused_destination")
        _logger.info("Link preview blocked for %s: %s", url, refusal)
        return False
    except requests.exceptions.RequestException as error:
        _debug.logic("preview_failed", error=type(error).__name__)
        return False
    except LocationParseError:
        _debug.logic("preview_failed", error="LocationParseError")
        return False
    with response:
        if not response.ok or not response.headers.get("Content-Type"):
            _debug.logic(
                "preview_skipped",
                status=response.status_code,
                content_type=response.headers.get("Content-Type"),
            )
            return False
        content_type = response.headers["Content-Type"].split(";")
        if response.headers["Content-Type"].startswith("image/"):
            return {
                "image_mimetype": content_type[0],
                "og_image": url,
                "source_url": url,
            }
        elif response.headers["Content-Type"].startswith("text/html"):
            return get_link_preview_from_html(url, response, deadline)
        return False


def get_link_preview_from_html(
    url: str, response: requests.Response, deadline: float | None = None
) -> dict[str, Any] | Literal[False]:
    content = b""
    for chunk in response.iter_content(chunk_size=HEAD_SCAN_CHUNK_SIZE):
        content += chunk
        pos = content.find(b"</head>", -2 * HEAD_SCAN_CHUNK_SIZE)
        if pos != -1:
            content = content[: pos + 7]
            break
        if len(content) > MAX_HEAD_BYTES:
            break
        if deadline is not None and time.monotonic() > deadline:
            _logger.info("Link preview timed out (body scan) for: %s", url)
            break

    if not content:
        return False
    _debug.perf.count(
        "head_scanned", bytes=len(content), truncated=len(content) > MAX_HEAD_BYTES
    )

    header_declared_charset = (
        "charset=" in response.headers.get("Content-Type", "").lower()
    )
    if header_declared_charset:
        encoding = response.encoding
    else:
        try:
            content.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            encoding = (
                response.encoding or chardet.detect(content).get("encoding") or "utf-8"
            )
    try:
        decoded_content = content.decode(encoding)
    except UnicodeDecodeError, TypeError:
        decoded_content = content.decode("utf-8", errors="ignore")

    try:
        tree = html.fromstring(decoded_content)
    except ValueError:
        decoded_content = re.sub(
            r"^<\?xml[^>]+\?>\s*", "", decoded_content, flags=re.IGNORECASE
        )
        tree = html.fromstring(decoded_content)

    og_title = tree.xpath('//meta[@property="og:title"]/@content')
    if og_title:
        og_title = og_title[0]
    elif tree.find(".//title") is not None:
        og_title = tree.find(".//title").text
    else:
        return False
    og_description = tree.xpath('//meta[@property="og:description"]/@content')
    og_type = tree.xpath('//meta[@property="og:type"]/@content')
    og_site_name = tree.xpath('//meta[@property="og:site_name"]/@content')
    og_image = tree.xpath('//meta[@property="og:image"]/@content')
    og_mimetype = tree.xpath('//meta[@property="og:image:type"]/@content')
    return {
        "og_description": og_description[0] if og_description else None,
        "og_image": og_image[0] if og_image else None,
        "og_mimetype": og_mimetype[0] if og_mimetype else None,
        "og_title": og_title,
        "og_type": og_type[0] if og_type else None,
        "og_site_name": og_site_name[0] if og_site_name else None,
        "source_url": url,
    }
