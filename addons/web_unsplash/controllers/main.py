import logging
import mimetypes
from urllib.parse import urlencode

import requests
import werkzeug.utils

from odoo import http, modules
from odoo.exceptions import UserError
from odoo.http import request
from odoo.libs.filesystem import guess_mimetype
from odoo.tools.image import image_process

from odoo.addons.html_editor.controllers.main import HTML_Editor

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


class Web_Unsplash(HTML_Editor):
    def _get_access_key(self):
        return request.env["credential.credential"]._get_system_secret(
            "unsplash.access_key"
        )

    def _notify_download(self, url):
        try:
            if (
                not url.startswith("https://api.unsplash.com/photos/")
                and not modules.module.current_test
            ):
                raise ValueError("ERROR: Unknown Unsplash notify URL!")
            access_key = self._get_access_key()
            request.env["ir.egress"].request(
                "GET",
                url,
                purpose="unsplash",
                params=urlencode({"client_id": access_key}),
                timeout=REQUEST_TIMEOUT,
            )
        except Exception:
            logger.exception("Unsplash download notification failed")

    @http.route(
        "/web_unsplash/attachment/add", type="jsonrpc", auth="user", methods=["POST"]
    )
    def save_unsplash_url(self, unsplashurls=None, **kwargs):

        def slugify(s):
            return "".join([c for c in s if c.isalnum() or c in list("- ")])[:1024]

        if not unsplashurls:
            return []

        uploads = []

        query = kwargs.get("query", "")
        query = slugify(query)

        res_model = kwargs.get("res_model", "ir.ui.view")
        res_id = None
        if res_model != "ir.ui.view" and kwargs.get("res_id"):
            try:
                res_id = int(kwargs["res_id"])
            except TypeError, ValueError:
                res_id = None

        for key, value in unsplashurls.items():
            url = value.get("url")
            if not url:
                logger.error("ERROR: Unknown Unsplash URL!: %s", url)
                continue
            try:
                if (
                    not url.startswith(
                        ("https://images.unsplash.com/", "https://plus.unsplash.com/")
                    )
                    and not modules.module.current_test
                ):
                    logger.error("ERROR: Unknown Unsplash URL!: %s", url)
                    raise ValueError("ERROR: Unknown Unsplash URL!")

                req = request.env["ir.egress"].request(
                    "GET", url, purpose="unsplash", timeout=REQUEST_TIMEOUT
                )
                if req.status_code != requests.codes.ok:
                    continue

                image = req.content

                image = image_process(image, verify_resolution=True)
                mimetype = guess_mimetype(image)
            except requests.exceptions.RequestException, UserError, ValueError:
                logger.exception("Failed to fetch or process Unsplash image")
                continue

            image_query = query + (mimetypes.guess_extension(mimetype) or "")

            url_frags = ["unsplash", key, image_query]

            attachment_data = {
                "name": "_".join(url_frags),
                "url": "/" + "/".join(url_frags),
                "data": image,
                "res_id": res_id,
                "res_model": res_model,
            }
            attachment = self._attachment_create(**attachment_data)
            if value.get("description"):
                attachment.description = value.get("description")
            attachment.generate_access_token()
            uploads.append(attachment._get_media_info())

            self._notify_download(value.get("download_url"))

        return uploads

    @http.route("/web_unsplash/fetch_images", type="jsonrpc", auth="user")
    def get_unsplash_images(self, **post):
        access_key = self._get_access_key()
        app_id = self.get_unsplash_app_id()
        if not access_key or not app_id:
            if not request.env.user._can_manage_unsplash_settings():
                return {"error": "no_access"}
            return {"error": "key_not_found"}
        post["client_id"] = access_key
        response = request.env["ir.egress"].request(
            "GET",
            "https://api.unsplash.com/search/photos/",
            purpose="unsplash",
            params=urlencode(post),
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == requests.codes.ok:
            return response.json()
        else:
            if not request.env.user._can_manage_unsplash_settings():
                return {"error": "no_access"}
            return {"error": response.status_code}

    @http.route("/web_unsplash/get_app_id", type="jsonrpc", auth="public")
    def get_unsplash_app_id(self, **post):
        return request.env["ir.config_parameter"].sudo().get_param("unsplash.app_id")

    @http.route("/web_unsplash/save_unsplash", type="jsonrpc", auth="user")
    def save_unsplash(self, **post):
        if request.env.user._can_manage_unsplash_settings():
            request.env["ir.config_parameter"].sudo().set_param(
                "unsplash.app_id", post.get("appId")
            )
            request.env["credential.credential"]._set_system_secret(
                "unsplash.access_key", post.get("key")
            )
            return True
        raise werkzeug.exceptions.NotFound
