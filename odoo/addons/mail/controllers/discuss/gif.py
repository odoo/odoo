# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
import werkzeug.urls

from odoo.http import request, route, Controller


class DiscussGifController(Controller):
    def _request_gifs(self, endpoint):
        response = requests.get(
            f"https://tenor.googleapis.com/v2/{endpoint}", timeout=3
        )
        response.raise_for_status()
        return response

    @route("/discuss/gif/search", type="json", auth="user")
    def search(self, search_term, locale="en", country="US", position=None):
        # sudo: ir.config_parameter - read keys are hard-coded and values are only used for server requests
        ir_config = request.env["ir.config_parameter"].sudo()
        query_string = werkzeug.urls.url_encode(
            {
                "q": search_term,
                "key": ir_config.get_param("discuss.tenor_api_key"),
                "client_key": request.env.cr.dbname,
                "limit": ir_config.get_param("discuss.tenor_gif_limit"),
                "contentfilter": ir_config.get_param("discuss.tenor_content_filter"),
                "locale": locale,
                "country": country,
                "media_filter": "tinygif",
                "pos": position,
            }
        )
        response = self._request_gifs(f"search?{query_string}")
        if response:
            return response.json()

    @route("/discuss/gif/categories", type="json", auth="user")
    def categories(self, locale="en", country="US"):
        # sudo: ir.config_parameter - read keys are hard-coded and values are only used for server requests
        ir_config = request.env["ir.config_parameter"].sudo()
        query_string = werkzeug.urls.url_encode(
            {
                "key": ir_config.get_param("discuss.tenor_api_key"),
                "client_key": request.env.cr.dbname,
                "limit": ir_config.get_param("discuss.tenor_gif_limit"),
                "contentfilter": ir_config.get_param("discuss.tenor_content_filter"),
                "locale": locale,
                "country": country,
            }
        )
        response = self._request_gifs(f"categories?{query_string}")
        if response:
            return response.json()

    @route("/discuss/gif/add_favorite", type="json", auth="user")
    def add_favorite(self, tenor_gif_id):
        request.env["discuss.gif.favorite"].create({"tenor_gif_id": tenor_gif_id})

    def _gif_posts(self, ids):
        # sudo: ir.config_parameter - read keys are hard-coded and values are only used for server requests
        ir_config = request.env["ir.config_parameter"].sudo()
        query_string = werkzeug.urls.url_encode(
            {
                "ids": ",".join(ids),
                "key": ir_config.get_param("discuss.tenor_api_key"),
                "client_key": request.env.cr.dbname,
                "media_filter": "tinygif",
            }
        )
        response = self._request_gifs(f"posts?{query_string}")
        if response:
            return response.json()["results"]

    @route("/discuss/gif/favorites", type="json", auth="user")
    def get_favorites(self, offset=0):
        tenor_gif_ids = request.env["discuss.gif.favorite"].search(
            [("create_uid", "=", request.env.user.id)], limit=20, offset=offset
        )
        return (self._gif_posts(tenor_gif_ids.mapped("tenor_gif_id")) or [],)

    @route("/discuss/gif/remove_favorite", type="json", auth="user")
    def remove_favorite(self, tenor_gif_id):
        request.env["discuss.gif.favorite"].search(
            [
                ("create_uid", "=", request.env.user.id),
                ("tenor_gif_id", "=", tenor_gif_id),
            ]
        ).unlink()
