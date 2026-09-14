import io
import logging
from functools import lru_cache, partial
from urllib.parse import parse_qsl, urlencode, urlparse

from PIL import Image, ImageColor, ImageDraw, ImageFont
from werkzeug.utils import send_file

from odoo import http, models
from odoo.exceptions import AccessError
from odoo.http import STATIC_CACHE, NotFound, Response, request
from odoo.libs.debug_log import DebugLog
from odoo.tools import consteq
from odoo.tools.misc import file_open

from odoo.addons.mail.tools.discuss import add_guest_to_context

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

MAX_ICON_GLYPHS = 8


@lru_cache(maxsize=4)
def _read_font(path: str) -> bytes:
    with file_open(path, "rb") as font_file:
        return font_file.read()


class MailController(http.Controller):
    _OI_FONT_CHAR_CODES = {
        "61569": "59464",
        "61593": "59418",
        "59407": "59407",
        "59409": "59409",
        "59416": "59416",
        "59417": "59417",
        "59419": "59419",
        "59420": "59420",
        "59421": "59421",
    }

    @classmethod
    def _redirect_to_generic_fallback(
        cls,
        model: str | None,
        res_id: int,
        access_token: str | None = None,
        **kwargs,
    ) -> Response:
        if request.session.uid is None:
            return cls._redirect_to_login_with_mail_view(
                model,
                res_id,
                access_token=access_token,
                **kwargs,
            )
        return cls._redirect_to_messaging()

    @classmethod
    def _redirect_to_messaging(cls) -> Response:
        url = "/odoo/action-mail.action_discuss"
        return request.redirect(url)

    @classmethod
    def _redirect_to_login_with_mail_view(
        cls,
        model: str | None,
        res_id: int,
        access_token: str | None = None,
        **kwargs,
    ) -> Response:
        url_base = "/mail/view"
        url_params = request.env["mixin.mail.thread"]._get_action_link_params(
            "view",
            **{
                "model": model,
                "res_id": res_id,
                "access_token": access_token,
                **kwargs,
            },
        )
        mail_view_url = f"{url_base}?{urlencode(sorted(url_params.items()))}"
        return request.redirect(f"/web/login?{urlencode({'redirect': mail_view_url})}")

    @classmethod
    def _is_token_valid(cls, token: str) -> bool:
        base_link = request.httprequest.path
        MailThread = request.env["mixin.mail.thread"]
        params = {
            key: value
            for key, value in request.params.items()
            if key in MailThread._ACTION_LINK_SIGNED_PARAMS
        }
        token = str(token)
        if consteq(MailThread._encode_link(base_link, params), token):
            _debug.logic("action_token", path=base_link, by="hmac")
            return True
        if consteq(MailThread._encode_link_legacy_sha1(base_link, params), token):
            _debug.logic("action_token", path=base_link, by="legacy_sha1")
            _logger.info(
                "Accepted a legacy SHA-1 action link token on route %s",
                request.httprequest.path,
            )
            return True
        return False

    @classmethod
    def _get_token_record_and_redirect(
        cls, model: str, res_id: int, token: str
    ) -> tuple:
        comparison = cls._is_token_valid(token)
        if not comparison:
            _debug.logic("action_token_invalid", model=model, record=res_id)
            _logger.warning("Invalid token in route %s", request.httprequest.url)
            return comparison, None, cls._redirect_to_generic_fallback(model, res_id)
        try:
            record = request.env[model].browse(res_id).exists()
        except Exception:
            record = None
            redirect = cls._redirect_to_generic_fallback(model, res_id)
        else:
            redirect = cls._redirect_to_record(model, res_id)
        return comparison, record, redirect

    @classmethod
    def _redirect_to_record(
        cls,
        model: str | None,
        res_id: int,
        access_token: str | None = None,
        **kwargs,
    ) -> Response:
        uid = request.session.uid
        user = request.env["res.users"].sudo().browse(uid)
        cids = []
        fallback = partial(
            cls._redirect_to_generic_fallback,
            model,
            res_id,
            access_token=access_token,
            **kwargs,
        )
        login = partial(
            cls._redirect_to_login_with_mail_view,
            model,
            res_id,
            access_token=access_token,
            **kwargs,
        )

        if (
            not model
            or not res_id
            or model not in request.env
            or request.env[model]._abstract
        ):
            return fallback()

        RecordModel = request.env[model]
        record_sudo = RecordModel.sudo().browse(res_id).exists()
        if not record_sudo:
            _debug.logic("redirect", model=model, record=res_id, by="missing")
            return fallback()

        suggested_company = record_sudo._get_redirect_suggested_company()
        if uid is not None:
            if not RecordModel.with_user(uid).has_access("read"):
                _debug.logic("redirect", model=model, record=res_id, by="no_access")
                return fallback()
            try:
                cids = cls._get_allowed_company_ids(
                    record_sudo, uid, user, suggested_company
                )
            except AccessError:
                _debug.logic("redirect", model=model, record=res_id, by="company")
                return fallback()
            record_action = record_sudo._get_access_action(access_uid=uid)
        else:
            record_action = record_sudo._get_access_action()
            if (
                record_action["type"] == "ir.actions.act_url"
                and record_action.get("target_type") != "public"
            ):
                _debug.logic("redirect", model=model, record=res_id, by="login")
                return login()

        record_action.pop("target_type", None)
        _debug.logic(
            "redirect",
            model=model,
            record=res_id,
            uid=uid,
            by=record_action["type"],
            companies=len(cids),
        )
        if record_action["type"] == "ir.actions.act_url":
            return request.redirect(
                cls._get_url_with_highlight(
                    record_action["url"], kwargs.get("highlight_message_id")
                )
            )
        elif record_action["type"] != "ir.actions.act_window":
            return cls._redirect_to_messaging()

        if (uid is None or request.env.user._is_public()) and not record_sudo.with_user(
            request.env.user
        ).has_access("read"):
            return login()

        if cids:
            request.future_response.set_cookie(
                "cids", "-".join([str(cid) for cid in cids])
            )
        return request.redirect(
            cls._get_record_backend_url(
                model, res_id, record_sudo, kwargs.get("highlight_message_id")
            )
        )

    @classmethod
    def _get_allowed_company_ids(
        cls,
        record_sudo: models.Model,
        uid: int,
        user: models.Model,
        suggested_company: models.Model,
    ) -> list[int]:
        cids_str = request.cookies.get("cids", str(user.company_id.id))
        try:
            cids = [int(cid) for cid in cids_str.split("-")]
        except ValueError:
            cids = [user.company_id.id]
        try:
            record_sudo.with_user(uid).with_context(
                allowed_company_ids=cids
            ).check_access("read")
        except AccessError:
            if not suggested_company:
                raise AccessError(
                    request.env._(
                        "There is no candidate company that has read access to the record."
                    )
                ) from None
            cids += [suggested_company.id]
            record_sudo.with_user(uid).with_context(
                allowed_company_ids=cids
            ).check_access("read")
            request.future_response.set_cookie(
                "cids", "-".join([str(cid) for cid in cids])
            )
        return cids

    @classmethod
    def _get_url_with_highlight(cls, url: str, highlight_message_id: int | None) -> str:
        if not highlight_message_id:
            return url
        parsed_url = urlparse(url)
        return parsed_url._replace(
            query=urlencode(
                parse_qsl(parsed_url.query)
                + [("highlight_message_id", highlight_message_id)]
            )
        ).geturl()

    @classmethod
    def _get_record_backend_url(
        cls,
        model: str,
        res_id: int,
        record_sudo: models.Model,
        highlight_message_id: int | None,
    ) -> str:
        url_params = {}
        menu_id = request.env["ir.ui.menu"]._get_best_backend_root_menu_id_for_model(
            model
        )
        if menu_id:
            url_params["menu_id"] = menu_id
        view_id = record_sudo.get_formview_id()
        if view_id:
            url_params["view_id"] = view_id
        if highlight_message_id:
            url_params["highlight_message_id"] = highlight_message_id
        model_in_url = model if "." in model else "m-" + model
        return f"/odoo/{model_in_url}/{res_id}?{urlencode(sorted(url_params.items()))}"

    @http.route("/mail/view", type="http", auth="public")
    def mail_action_view(
        self,
        model: str | None = None,
        res_id: int | str | None = None,
        access_token: str | None = None,
        **kwargs,
    ) -> Response:
        if kwargs.get("message_id"):
            try:
                message = request.env["mail.message"].search(
                    [("id", "=", int(kwargs["message_id"]))]
                )
            except ValueError, TypeError:
                message = request.env["mail.message"]
            if message:
                model, res_id = message.model, message.res_id

        if res_id and isinstance(res_id, str):
            try:
                res_id = int(res_id)
            except ValueError:
                res_id = False
        return self._redirect_to_record(model, res_id, access_token, **kwargs)

    @http.route("/mail/unfollow", type="http", auth="public", csrf=False)
    def mail_action_unfollow(  # noqa: E8528 - a link from an email, authorised by the record token
        self, model: str, res_id: str, pid: str, token: str, **kwargs
    ) -> Response:
        try:
            res_id, pid = int(res_id), int(pid)
        except TypeError, ValueError:
            raise NotFound from None
        comparison, record, __ = MailController._get_token_record_and_redirect(
            model, res_id, token
        )
        if not comparison or not record:
            raise AccessError(request.env._("Non existing record or wrong token."))
        if not isinstance(record, request.env.registry["mixin.mail.thread"]):
            raise NotFound

        record_sudo = record.sudo()
        _debug.lifecycle("unfollow_link", model=model, record=res_id, partner=pid)
        record_sudo.message_unsubscribe([pid])

        display_link = True
        if request.session.uid:
            display_link = record.has_access("read")

        return request.render(
            "mail.message_document_unfollowed",
            {
                "name": record_sudo.display_name,
                "model_name": request.env["ir.model"].sudo()._get(model).display_name,
                "access_url": record._notify_get_action_link(
                    "view", model=model, res_id=res_id
                )
                if display_link
                else False,
            },
        )

    @http.route("/mail/message/<int:message_id>", type="http", auth="public")
    @add_guest_to_context
    def mail_thread_message_redirect(self, message_id: int, **kwargs) -> Response:
        message = request.env["mail.message"].search([("id", "=", message_id)])
        if not message:
            if request.env.user._is_public():
                return request.redirect(
                    f"/web/login?redirect=/mail/message/{message_id}"
                )
            raise NotFound

        return self._redirect_to_record(
            message.model, message.res_id, highlight_message_id=message_id
        )

    @http.route(
        [
            "/web_editor/font_to_img/<icon>",
            "/web_editor/font_to_img/<icon>/<color>",
            "/web_editor/font_to_img/<icon>/<color>/<int:size>",
            "/web_editor/font_to_img/<icon>/<color>/<int:width>x<int:height>",
            "/web_editor/font_to_img/<icon>/<color>/<int:size>/<int:alpha>",
            "/web_editor/font_to_img/<icon>/<color>/<int:width>x<int:height>/<int:alpha>",
            "/web_editor/font_to_img/<icon>/<color>/<bg>",
            "/web_editor/font_to_img/<icon>/<color>/<bg>/<int:size>",
            "/web_editor/font_to_img/<icon>/<color>/<bg>/<int:width>x<int:height>",
            "/web_editor/font_to_img/<icon>/<color>/<bg>/<int:width>x<int:height>/<int:alpha>",
            "/mail/font_to_img/<icon>",
            "/mail/font_to_img/<icon>/<color>",
            "/mail/font_to_img/<icon>/<color>/<int:size>",
            "/mail/font_to_img/<icon>/<color>/<int:width>x<int:height>",
            "/mail/font_to_img/<icon>/<color>/<int:size>/<int:alpha>",
            "/mail/font_to_img/<icon>/<color>/<int:width>x<int:height>/<int:alpha>",
            "/mail/font_to_img/<icon>/<color>/<bg>",
            "/mail/font_to_img/<icon>/<color>/<bg>/<int:size>",
            "/mail/font_to_img/<icon>/<color>/<bg>/<int:width>x<int:height>",
            "/mail/font_to_img/<icon>/<color>/<bg>/<int:width>x<int:height>/<int:alpha>",
        ],
        type="http",
        auth="none",
    )
    def export_icon_to_png(
        self,
        icon: str,
        color: str = "#000",
        bg: str | None = None,
        size: int = 100,
        alpha: int = 255,
        width: int | None = None,
        height: int | None = None,
    ) -> Response:
        if len(icon) > MAX_ICON_GLYPHS:
            raise NotFound

        font = "/web/static/src/libs/fontawesome7/webfonts/fa-solid-900.woff2"
        if icon.isdigit() and icon in self._OI_FONT_CHAR_CODES:
            icon = self._OI_FONT_CHAR_CODES[icon]
            font = "/web/static/lib/odoo_ui_icons/fonts/odoo_ui_icons.woff"

        size = max(width, height, 1) if width else size
        width = width or size
        height = height or size
        width = max(1, min(width, 512))
        height = max(1, min(height, 512))
        font_obj = ImageFont.truetype(
            io.BytesIO(_read_font(font.removeprefix("/"))), height
        )

        if icon.isdigit():
            code = int(icon)
            if code > 0x10FFFF:
                raise NotFound
            icon = chr(code)

        if bg is not None and bg.startswith("rgba"):
            bg = bg.replace("rgba", "rgb")
            bg = ",".join(bg.split(",")[:-1]) + ")"

        if color is not None and color.startswith("rgba"):
            color = color.replace("rgba", "rgb")
            color = ",".join(color.split(",")[:-1]) + ")"

        for _color in (color, bg):
            if _color is not None:
                try:
                    ImageColor.getrgb(_color)
                except ValueError:
                    raise NotFound from None

        alpha = max(0, min(alpha, 255))

        dummy = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy)
        bbox = draw.textbbox((0, 0), icon, font=font_obj)
        boxw = max(1, min(bbox[2] - bbox[0], 512))

        outimage = Image.new("RGBA", (boxw, height), bg or (0, 0, 0, 0))
        if alpha == 255:
            draw = ImageDraw.Draw(outimage)
            draw.text((0, 0), icon, font=font_obj, fill=color)
        else:
            glyph = Image.new("RGBA", outimage.size, (0, 0, 0, 0))
            ImageDraw.Draw(glyph).text((0, 0), icon, font=font_obj, fill=color)
            glyph.putalpha(glyph.getchannel("A").point(lambda a: a * alpha // 255))
            outimage = Image.alpha_composite(outimage, glyph)

        output = io.BytesIO()
        outimage.save(output, format="PNG")
        output.seek(0)
        response = send_file(
            output,
            request.httprequest.environ,
            mimetype="image/png",
            conditional=False,
            etag=False,
            max_age=STATIC_CACHE,
            response_class=Response,
        )
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST"
        return response
