import logging

from odoo import http

from odoo.addons.mail.controllers.mail import MailController

_logger = logging.getLogger(__name__)


class CrmController(http.Controller):
    @http.route("/lead/case_mark_won", type="http", auth="user", methods=["GET"])
    def crm_lead_case_mark_won(self, res_id, token):
        comparison, record, redirect = MailController._get_token_record_and_redirect(
            "crm.lead", int(res_id), token
        )
        if comparison and record:
            try:
                record.action_set_won_rainbowman()
            except Exception:
                _logger.exception("Could not mark crm.lead as won")
                return MailController._redirect_to_generic_fallback("crm.lead", res_id)
        return redirect

    @http.route("/lead/case_mark_lost", type="http", auth="user", methods=["GET"])
    def crm_lead_case_mark_lost(self, res_id, token):
        comparison, record, redirect = MailController._get_token_record_and_redirect(
            "crm.lead", int(res_id), token
        )
        if comparison and record:
            try:
                record.action_set_lost()
            except Exception:
                _logger.exception("Could not mark crm.lead as lost")
                return MailController._redirect_to_generic_fallback("crm.lead", res_id)
        return redirect

    @http.route("/lead/convert", type="http", auth="user", methods=["GET"])
    def crm_lead_convert(self, res_id, token):
        comparison, record, redirect = MailController._get_token_record_and_redirect(
            "crm.lead", int(res_id), token
        )
        if comparison and record:
            try:
                record.convert_opportunity(record.partner_id)
            except Exception:
                _logger.exception("Could not convert crm.lead to opportunity")
                return MailController._redirect_to_generic_fallback("crm.lead", res_id)
        return redirect
