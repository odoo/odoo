# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from openerp.addons.mail.controllers.main import MailController
from openerp import http, _
from openerp.http import request

_logger = logging.getLogger(__name__)


class HrHolidaysController(http.Controller):

    @http.route('/hr_holidays/validate', type='http', auth='user', methods=['GET'])
    def hr_holidays_validate(self, res_id, token):
        if not MailController._check_token(token):
            _logger.warning(_('Invalid token in route %s') % request.httprequest.url)
            return MailController._redirect_to_messaging()
        try:
            request.env['hr.holidays'].browse(int(res_id)).exists().signal_workflow('validate')
        except:
            return MailController._redirect_to_messaging()
        return MailController._redirect_to_record('hr.holidays', res_id)

    @http.route('/hr_holidays/refuse', type='http', auth='user', methods=['GET'])
    def hr_holidays_refuse(self, res_id, token):
        if not MailController._check_token(token):
            _logger.warning(_('Invalid token in route %s') % request.httprequest.url)
            return MailController._redirect_to_messaging()
        try:
            request.env['hr.holidays'].browse(int(res_id)).exists().signal_workflow('refuse')
        except:
            return MailController._redirect_to_messaging()
        return MailController._redirect_to_record('hr.holidays', res_id)
