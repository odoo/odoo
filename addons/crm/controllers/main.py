# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers.main import MailController
from odoo import http


class CrmController(http.Controller):

    @http.route('/lead/case_mark_won', type='http', auth='user', methods=['GET'])
    def crm_lead_case_mark_won(self, res_id, token):
        comparison, record, redirect = MailController._check_token_and_record_or_redirect('crm.lead', int(res_id), token)
        if comparison and record:
            try:
                record.case_mark_won()
            except Exception:
                return MailController._redirect_to_messaging()
        return redirect

    @http.route('/lead/case_mark_lost', type='http', auth='user', methods=['GET'])
    def crm_lead_case_mark_lost(self, res_id, token):
        comparison, record, redirect = MailController._check_token_and_record_or_redirect('crm.lead', int(res_id), token)
        if comparison and record:
            try:
                record.case_mark_lost()
            except Exception:
                return MailController._redirect_to_messaging()
        return redirect

    @http.route('/lead/convert', type='http', auth='user', methods=['GET'])
    def crm_lead_convert(self, res_id, token):
        comparison, record, redirect = MailController._check_token_and_record_or_redirect('crm.lead', int(res_id), token)
        if comparison and record:
            try:
                record.convert_opportunity(record.partner_id.id)
            except Exception:
                return MailController._redirect_to_messaging()
        return redirect
