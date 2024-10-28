# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers.mail import MailController
from odoo import http
from datetime import date

class HrHolidaysController(http.Controller):

    @http.route('/leave/approve', type='http', auth='user', methods=['GET'])
    def hr_holidays_request_approve(self, res_id, token):
        comparison, record, redirect = MailController._check_token_and_record_or_redirect('hr.leave', int(res_id), token)
        if comparison and record:
            try:
                record.action_approve()
            except Exception:
                return MailController._redirect_to_messaging()
        return redirect

    @http.route('/leave/validate', type='http', auth='user', methods=['GET'])
    def hr_holidays_request_validate(self, res_id, token):
        comparison, record, redirect = MailController._check_token_and_record_or_redirect('hr.leave', int(res_id), token)
        if comparison and record:
            try:
                record.action_validate()
            except Exception:
                return MailController._redirect_to_messaging()
        return redirect

    @http.route('/leave/refuse', type='http', auth='user', methods=['GET'])
    def hr_holidays_request_refuse(self, res_id, token):
        comparison, record, redirect = MailController._check_token_and_record_or_redirect('hr.leave', int(res_id), token)
        if comparison and record:
            try:
                record.action_refuse()
            except Exception:
                return MailController._redirect_to_messaging()
        return redirect

    @http.route('/allocation/validate', type='http', auth='user', methods=['GET'])
    def hr_holidays_allocation_validate(self, res_id, token):
        comparison, record, redirect = MailController._check_token_and_record_or_redirect('hr.leave.allocation', int(res_id), token)
        if comparison and record:
            try:
                record.action_approve()
            except Exception:
                return MailController._redirect_to_messaging()
        return redirect

    @http.route('/allocation/refuse', type='http', auth='user', methods=['GET'])
    def hr_holidays_allocation_refuse(self, res_id, token):
        comparison, record, redirect = MailController._check_token_and_record_or_redirect('hr.leave.allocation', int(res_id), token)
        if comparison and record:
            try:
                record.action_refuse()
            except Exception:
                return MailController._redirect_to_messaging()
        return redirect

    @http.route('/hr_holidays/get_public_holidays', type='jsonrpc', auth='user')
    def hr_holidays_get_public_holidays(self):
        today = date.today()
        isPublicHoliday = bool(http.request.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('company_id', 'in', self.env.company.ids),
            ('date_from', '<=', today),
            ('date_to', '>=', today),
        ], limit=1))
        return isPublicHoliday
