import logging

from odoo import http
from odoo.http import request

from odoo.addons.mail.controllers.mail import MailController

_logger = logging.getLogger(__name__)


class HrHolidaysController(http.Controller):
    def _act_on_token(self, model, res_id, token, action):
        try:
            record_id = int(res_id)
        except TypeError, ValueError:
            _logger.warning("%s: non-numeric res_id %r from %s", model, res_id, action)
            return request.redirect("/odoo")
        comparison, record, redirect = MailController._get_token_record_and_redirect(
            model, record_id, token
        )
        if comparison and record:
            try:
                getattr(record, action)()
            except Exception:
                _logger.warning(
                    "%s(%s) failed for user %s via %s",
                    action,
                    record_id,
                    request.env.uid,
                    model,
                    exc_info=True,
                )
                return MailController._redirect_to_generic_fallback(model, record_id)
        return redirect

    @http.route(
        ["/leave/approve", "/leave/validate"], type="http", auth="user", methods=["GET"]
    )
    def hr_holidays_request_approve(self, res_id, token):
        return self._act_on_token("hr.leave", res_id, token, "action_approve")

    @http.route("/leave/refuse", type="http", auth="user", methods=["GET"])
    def hr_holidays_request_refuse(self, res_id, token):
        return self._act_on_token("hr.leave", res_id, token, "action_refuse")

    @http.route("/allocation/validate", type="http", auth="user", methods=["GET"])
    def hr_holidays_allocation_validate(self, res_id, token):
        return self._act_on_token(
            "hr.leave.allocation", res_id, token, "action_approve"
        )

    @http.route("/allocation/refuse", type="http", auth="user", methods=["GET"])
    def hr_holidays_allocation_refuse(self, res_id, token):
        return self._act_on_token("hr.leave.allocation", res_id, token, "action_refuse")
