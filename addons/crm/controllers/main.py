# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from openerp.addons.mail.controllers.main import MailController
from openerp import http, _
from openerp.http import request

_logger = logging.getLogger(__name__)


class CrmController(http.Controller):

    @http.route('/lead/case_mark_won', type='http', auth='user', methods=['GET'])
    def crm_lead_case_mark_won(self, res_id, token):
        if not MailController._check_token(token):
            _logger.warning(_('Invalid token in route %s') % request.httprequest.url)
            return self._redirect_to_messaging()
        try:
            request.env['crm.lead'].browse(int(res_id)).exists().case_mark_won()
        except:
            return MailController._redirect_to_messaging()
        return MailController._redirect_to_record('crm.lead', res_id)

    @http.route('/lead/case_mark_lost', type='http', auth='user', methods=['GET'])
    def crm_lead_case_mark_lost(self, res_id, token):
        if not MailController._check_token(token):
            _logger.warning(_('Invalid token in route %s') % request.httprequest.url)
            return self._redirect_to_messaging()
        try:
            request.env['crm.lead'].browse(int(res_id)).exists().case_mark_lost()
        except:
            return MailController._redirect_to_messaging()
        return MailController._redirect_to_record('crm.lead', res_id)

    @http.route('/lead/convert', type='http', auth='user', methods=['GET'])
    def crm_lead_convert(self, res_id, token):
        if not MailController._check_token(token):
            _logger.warning(_('Invalid token in route %s') % request.httprequest.url)
            return self._redirect_to_messaging()
        try:
            lead = request.env['crm.lead'].browse(int(res_id)).exists()
            if lead.type == 'lead':
                lead.convert_opportunity(lead.partner_id.id)
        except:
            return MailController._redirect_to_messaging()
        return MailController._redirect_to_record('crm.lead', res_id)
