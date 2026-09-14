import logging
import typing
from datetime import timedelta

import babel
import requests

from odoo import fields
from odoo.http import Controller, NotFound, request, route
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.controllers.utils import to_record_id

if typing.TYPE_CHECKING:
    from odoo.addons.mail.models.mail_message import MailMessage

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

TRANSLATION_DAILY_LIMIT_PARAM = "mail.translation.daily_limit"
TRANSLATION_DAILY_LIMIT_DEFAULT = 1000


class GoogleTranslateController(Controller):
    def _translation_rate_limited(self) -> bool:
        cap = request.env["ir.config_parameter"]._get_int_param(
            TRANSLATION_DAILY_LIMIT_PARAM, TRANSLATION_DAILY_LIMIT_DEFAULT
        )
        if cap <= 0:
            return False
        since = fields.Datetime.now() - timedelta(days=1)
        count = (
            request.env["mail.message.translation"]
            .sudo()
            .search_count(
                [("create_uid", "=", request.env.uid), ("create_date", ">=", since)]
            )
        )
        return count >= cap

    def _target_lang(self) -> str:
        lang = request.env.user.lang or request.env.lang or "en_US"
        return lang.split("_")[0]

    @route("/mail/message/translate", methods=["POST"], type="jsonrpc", auth="user")
    def translate(self, message_id: int) -> dict:
        message = request.env["mail.message"].search(
            [("id", "=", to_record_id(message_id))]
        )
        if not message:
            raise NotFound
        target_lang = self._target_lang()
        domain = [
            ("message_id", "=", message.id),
            ("target_lang", "=", target_lang),
        ]
        translation = request.env["mail.message.translation"].sudo().search(domain)
        _debug.logic(
            "translate",
            message=message.id,
            target_lang=target_lang,
            by="cache" if translation else "service",
        )
        if not translation:
            if self._translation_rate_limited():
                _debug.logic(
                    "translate_refused", message=message.id, reason="rate_limit"
                )
                return {
                    "error": request.env._(
                        "Translation rate limit reached, please retry later."
                    )
                }
            try:
                source_lang = self._get_source_lang(message)
                vals = {
                    "body": self._get_translation(
                        str(message.body), source_lang, target_lang
                    ),
                    "message_id": message.id,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                }
                translation = (
                    request.env["mail.message.translation"].sudo().create(vals)
                )
            except requests.exceptions.RequestException as err:
                _debug.logic(
                    "translate_failed", message=message.id, error=type(err).__name__
                )
                return {"error": self._translation_error_message(err)}
            except ValueError, KeyError, IndexError, TypeError:
                _debug.logic("translate_failed", message=message.id, error="payload")
                _logger.warning(
                    "Unexpected payload from the translation service", exc_info=True
                )
                return {
                    "error": request.env._("The translation service is unavailable.")
                }
        try:
            lang_name = babel.Locale(translation.source_lang).get_display_name(
                request.env.user.lang or request.env.lang or "en_US"
            )
        except babel.UnknownLocaleError, ValueError:
            lang_name = translation.source_lang
        return {
            "body": translation.body,
            "lang_name": lang_name,
        }

    def _translation_error_message(
        self, err: requests.exceptions.RequestException
    ) -> str:
        response = getattr(err, "response", None)
        if response is not None:
            try:
                return response.json()["error"]["message"]
            except ValueError, KeyError, TypeError:
                pass
        return request.env._("The translation service is unavailable.")

    def _get_source_lang(self, message: MailMessage) -> str:
        translation = (
            request.env["mail.message.translation"]
            .sudo()
            .search([("message_id", "=", message.id)], limit=1, order="id")
        )
        if translation:
            return translation.source_lang
        response = self._post(endpoint="detect", data={"q": str(message.body)})
        return response.json()["data"]["detections"][0][0]["language"]

    def _get_translation(self, body: str, source_lang: str, target_lang: str) -> str:
        response = self._post(
            data={"q": body, "target": target_lang, "source": source_lang}
        )
        return response.json()["data"]["translations"][0]["translatedText"]

    def _post(self, endpoint: str = "", data: dict | None = None) -> requests.Response:
        api_key = request.env["credential.credential"]._get_system_secret(
            "mail.google_translate_api_key"
        )
        url = f"https://translation.googleapis.com/language/translate/v2/{endpoint}?key={api_key}"
        with _debug.perf(
            "translation_api_posted", endpoint=endpoint or "translate"
        ) as span:
            response = request.env["ir.egress"].request(
                "POST", url, purpose="google_translate", data=data, timeout=3
            )
            span.set(status=getattr(response, "status_code", None))
        response.raise_for_status()
        return response
