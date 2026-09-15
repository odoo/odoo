from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools import consteq

from odoo.addons.mail.controllers import mail
from odoo.addons.portal.utils import get_url_with_params

_debug = DebugLog(__name__)


class MailController(mail.MailController):
    @classmethod
    def _redirect_to_generic_fallback(cls, model, res_id, access_token=None, **kwargs):
        if request.session.uid and request.env.user.share:
            _debug.logic("mail_redirect", by="portal_home", model=model, record=res_id)
            return request.redirect("/my")
        return super()._redirect_to_generic_fallback(
            model, res_id, access_token=access_token, **kwargs
        )

    @classmethod
    def _redirect_to_record(cls, model, res_id, access_token=None, **kwargs):
        if (
            not model
            or not res_id
            or model not in request.env
            or request.env[model]._abstract
        ):
            return super()._redirect_to_record(
                model, res_id, access_token=access_token, **kwargs
            )

        if isinstance(request.env[model], request.env.registry["mixin.portal"]):
            uid = request.session.uid or request.env.ref("base.public_user").id
            record_sudo = request.env[model].sudo().browse(res_id).exists()
            try:
                record_sudo.with_user(uid).check_access("read")
            except AccessError:
                if (
                    record_sudo.access_token
                    and access_token
                    and consteq(record_sudo.access_token, access_token)
                ):
                    record_action = record_sudo._get_access_action(force_website=True)
                    if record_action["type"] == "ir.actions.act_url":
                        pid = kwargs.get("pid")
                        hash_param = kwargs.get("hash")
                        url = record_action["url"]
                        if pid and hash_param:
                            url = get_url_with_params(
                                url, {"pid": pid, "hash": hash_param}
                            )
                        _debug.logic(
                            "mail_redirect",
                            by="portal_token",
                            model=model,
                            record=res_id,
                        )
                        return request.redirect(url)
        return super()._redirect_to_record(
            model, res_id, access_token=access_token, **kwargs
        )

    @http.route("/mail/unfollow", type="http", website=True)
    def mail_action_unfollow(self, model, res_id, pid, token, **kwargs):
        return super().mail_action_unfollow(model, res_id, pid, token, **kwargs)
