# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)


class MailPluginController(http.Controller):

    @http.route('/mail_client_extension/log_single_mail_content', type="json", auth="outlook", cors="*")
    def log_single_mail_content(self, lead, message, **kw):
        crm_lead = request.env['crm.lead'].browse(lead)
        crm_lead.message_post(body=message)

    @http.route('/mail_client_extension/lead/get_by_partner_id', type="json", auth="outlook", cors="*")
    def crm_lead_get_by_partner_id(self, partner, limit, offset, **kwargs):
        partner_leads = request.env['crm.lead'].search([('partner_id', '=', partner)], offset=offset, limit=limit)
        leads = []
        for lead in partner_leads:
            leads.append({
                'id': lead.id,
                'name': lead.name,
                'expected_revenue': formatLang(request.env, lead.expected_revenue, monetary=True, currency_obj=lead.company_currency),
            })

        return {'leads': leads}

    @http.route('/mail_client_extension/lead/create_from_partner', type='http', auth='user', methods=['GET'])
    def crm_lead_redirect_form_view(self, partner_id):
        server_action = http.request.env.ref("crm_mail_client_extension.lead_creation_prefilled_action")
        return werkzeug.utils.redirect('/web#action=%s&model=crm.lead&partner_id=%s' % (server_action.id, int(partner_id)))
