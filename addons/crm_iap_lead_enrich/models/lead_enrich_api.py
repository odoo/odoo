# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.addons.iap import jsonrpc,InsufficientCreditError

DEFAULT_ENDPOINT = 'https://iap-services.odoo.com'


class LeadEnrichApi(models.AbstractModel):
    _name = 'crm_iap_lead_enrich.api'
    _description = 'Lead Enrichment API'
    
    @api.model
    def _make_request(self, domains):
        """This method will query the endpoint to get the data for the asked (lead.id, domain) pairs"""
        reveal_account = self.env['iap.account'].get('reveal')
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        endpoint = self.env['ir.config_parameter'].sudo().get_param('reveal.endpoint', DEFAULT_ENDPOINT) + '/iap/clearbit/1/lead_enrichment_email'
        params = {
            'account_token': reveal_account.account_token,
            'dbuuid': dbuuid,
            'domains': domains,
        }
        return jsonrpc(endpoint, params=params, timeout=300)