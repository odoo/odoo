import hashlib
import logging
from urllib.parse import urlencode

import requests

from odoo.http import Controller, NotFound, ServiceUnavailable, request, route
from odoo.libs.debug_log import DebugLog

KLIPY_CONTENT_FILTER = "medium"
KLIPY_GIF_LIMIT = 8

MAX_GIF_ID_LEN = 128

GIF_FAVORITES_PAGE = 20

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def _query_string(params: dict) -> str:
    return urlencode({key: value for key, value in params.items() if value is not None})


def _to_offset(offset: object) -> int:
    try:
        return max(0, int(offset))
    except TypeError, ValueError:
        return 0


class DiscussGifController(Controller):
    def _gif_client_key(self) -> str:
        return hashlib.sha256(request.env.cr.dbname.encode()).hexdigest()[:32]

    def _api_key(self) -> str:
        return (
            request.env["credential.credential"]._get_system_secret(
                "discuss.klipy_api_key"
            )
            or ""
        )

    def _request_gifs(self, endpoint: str) -> requests.Response:
        if not self._api_key():
            _debug.logic("gif_request_refused", reason="no_api_key")
            _logger.debug("Klipy GIF API is not configured; refusing the request.")
            raise ServiceUnavailable
        try:
            with _debug.perf(
                "gif_api_requested", endpoint=endpoint.partition("?")[0]
            ) as span:
                response = request.env["ir.egress"].request(
                    "GET",
                    f"https://api.klipy.com/v2/{endpoint}",
                    purpose="discuss_gif",
                    timeout=3,
                )
                span.set(status=getattr(response, "status_code", None))
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _debug.logic("gif_request_failed", error=type(e).__name__)
            _logger.warning("Klipy GIF API request failed: %s", e)
            raise ServiceUnavailable from None
        return response

    @route("/discuss/gif/search", type="jsonrpc", auth="user", readonly=True)
    def search(
        self,
        search_term: str,
        locale: str = "en",
        country: str = "US",
        position: str | None = None,
    ) -> dict:
        query_string = _query_string(
            {
                "q": search_term,
                "key": self._api_key(),
                "client_key": self._gif_client_key(),
                "limit": KLIPY_GIF_LIMIT,
                "contentfilter": KLIPY_CONTENT_FILTER,
                "locale": locale,
                "country": country,
                "media_filter": "tinygif",
                "pos": position,
            }
        )
        return self._request_gifs(f"search?{query_string}").json()

    @route("/discuss/gif/categories", type="jsonrpc", auth="user", readonly=True)
    def categories(self, locale: str = "en", country: str = "US") -> dict:
        query_string = _query_string(
            {
                "key": self._api_key(),
                "client_key": self._gif_client_key(),
                "limit": KLIPY_GIF_LIMIT,
                "contentfilter": KLIPY_CONTENT_FILTER,
                "locale": locale,
                "country": country,
            }
        )
        return self._request_gifs(f"categories?{query_string}").json()

    @staticmethod
    def _to_gif_id(tenor_gif_id: object) -> str:
        if isinstance(tenor_gif_id, int) and not isinstance(tenor_gif_id, bool):
            tenor_gif_id = str(tenor_gif_id)
        if (
            not isinstance(tenor_gif_id, str)
            or not 0 < len(tenor_gif_id) <= MAX_GIF_ID_LEN
        ):
            raise NotFound
        return tenor_gif_id

    @route("/discuss/gif/add_favorite", type="jsonrpc", auth="user")
    def add_favorite(self, tenor_gif_id: str) -> None:
        tenor_gif_id = self._to_gif_id(tenor_gif_id)
        favorites = request.env["discuss.gif.favorite"]
        if favorites.search_count(
            [
                ("create_uid", "=", request.env.user.id),
                ("tenor_gif_id", "=", tenor_gif_id),
            ],
            limit=1,
        ):
            return
        favorites.create({"tenor_gif_id": tenor_gif_id})

    def _gif_posts(self, ids: list[str]) -> list:
        query_string = _query_string(
            {
                "ids": ",".join(ids),
                "key": self._api_key(),
                "client_key": self._gif_client_key(),
                "media_filter": "tinygif",
            }
        )
        return self._request_gifs(f"posts?{query_string}").json()["results"]

    @route("/discuss/gif/favorites", type="jsonrpc", auth="user", readonly=True)
    def get_favorites(self, offset: int = 0) -> tuple:
        favorites = request.env["discuss.gif.favorite"].search(
            [("create_uid", "=", request.env.user.id)],
            limit=GIF_FAVORITES_PAGE + 1,
            offset=_to_offset(offset),
            order="id desc",
        )
        has_more = len(favorites) > GIF_FAVORITES_PAGE
        gif_ids = favorites[:GIF_FAVORITES_PAGE].mapped("tenor_gif_id")
        if not gif_ids:
            return ([], False)
        return (self._gif_posts(gif_ids) or [], has_more)

    @route("/discuss/gif/remove_favorite", type="jsonrpc", auth="user")
    def remove_favorite(self, tenor_gif_id: str) -> None:
        request.env["discuss.gif.favorite"].search(
            [
                ("create_uid", "=", request.env.user.id),
                ("tenor_gif_id", "=", self._to_gif_id(tenor_gif_id)),
            ]
        ).unlink()
