# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.mail.controllers.main import MailController
from openerp import http


class HrHolidaysController(http.Controller):

    @http.route('/hr_holidays/validate', type='http', auth='user', methods=['GET'])
    def hr_holidays_validate(self, res_id, token):
        comparison, record, redirect = MailController._check_token_and_record_or_redirect('hr.holidays', int(res_id), token)
        if comparison and record:
            try:
                record.signal_workflow('validate')
            except Exception:
                return MailController._redirect_to_messaging()
        return redirect

    @http.route('/hr_holidays/refuse', type='http', auth='user', methods=['GET'])
    def hr_holidays_refuse(self, res_id, token):
        comparison, record, redirect = MailController._check_token_and_record_or_redirect('hr.holidays', int(res_id), token)
        if comparison and record:
            try:
                record.signal_workflow('refuse')
            except Exception:
                return MailController._redirect_to_messaging()
        return redirect
