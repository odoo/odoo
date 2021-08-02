# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.tools import html2plaintext


class CrmClient(http.Controller):

    @http.route(route='/mail_client_extension/log_single_mail_content',
                type="json", auth="outlook", cors="*")
    def log_single_mail_content(self, lead, message, **kw):
        """
            deprecated as of saas-14.3, not needed for newer versions of the mail plugin but necessary
            for supporting older versions
        """
        crm_lead = request.env['crm.lead'].browse(lead)
        crm_lead.message_post(body=message)

    @http.route('/mail_client_extension/lead/get_by_partner_id', type="json", auth="outlook", cors="*")
    def crm_lead_get_by_partner_id(self, partner, limit=5, offset=0, **kwargs):
        """
            deprecated as of saas-14.3, not needed for newer versions of the mail plugin but necessary
            for supporting older versions
        """
        partner_instance = request.env['res.partner'].browse(partner)
        return {'leads': self._fetch_partner_leads(partner_instance, limit, offset)}

    @http.route('/mail_client_extension/lead/create_from_partner', type='http', auth='user', methods=['GET'])
    def crm_lead_redirect_create_form_view(self, partner_id):
        """
            deprecated as of saas-14.3, not needed for newer versions of the mail plugin but necessary
            for supporting older versions
        """
        server_action = http.request.env.ref("crm_mail_plugin.lead_creation_prefilled_action")
        return request.redirect(
            '/web#action=%s&model=crm.lead&partner_id=%s' % (server_action.id, int(partner_id)))

    @http.route('/mail_plugin/lead/create', type='json', auth='outlook', cors="*")
    def crm_lead_create(self, partner_id, email_body, email_subject):
        partner = request.env['res.partner'].browse(partner_id).exists()
        if not partner:
            return {'error': 'partner_not_found'}

        record = request.env['crm.lead'].create({
            'name': html2plaintext(email_subject),
            'partner_id': partner_id,
            'description': email_body,
        })

        return {'lead_id': record.id}

    @http.route('/mail_client_extension/lead/open', type='http', auth='user')
    def crm_lead_open(self, lead_id):
        """
            deprecated as of saas-14.3, not needed for newer versions of the mail plugin but necessary
            for supporting older versions
        """
        action = http.request.env.ref("crm.crm_lead_view_form")
        url = '/web#id=%s&action=%s&model=crm.lead&edit=1&model=crm.lead' % (lead_id, action.id)
        return request.redirect(url)
