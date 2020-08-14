# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.addons import iap


class IapEnrichAPI(models.AbstractModel):
    _name = 'iap.enrich.api'
    _description = 'IAP Lead Enrichment API'
    _DEFAULT_ENDPOINT = 'https://iap-services.odoo.com'

    @api.model
    def _contact_iap(self, local_endpoint, params):
        # Get IAP account model
        iap_account_model = self.env['iap.account']
        # Get current credits :
        # in 'get_credits' method : the targeted account getter is called with a 'force_create=False' (see iap.py > 'get_credits()')
        account_credits = iap_account_model.get_credits('reveal')
        # Test if credits min value reached
        if account_credits <= 5:
            # Send notification to admin : low credits on lead enrichment
            self._notify_admins(*self._get_admin_notification('iap__low_credits')(account_credits))
        account = iap_account_model.get('reveal')
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        params['account_token'] = account.account_token
        params['dbuuid'] = dbuuid
        base_url = self.env['ir.config_parameter'].sudo().get_param('enrich.endpoint', self._DEFAULT_ENDPOINT)
        return iap.jsonrpc(base_url + local_endpoint, params=params, timeout=300)

    @api.model
    def _request_enrich(self, lead_emails):
        """ Contact endpoint to get enrichment data.

        :param lead_emails: dict{lead_id: email}
        :return: dict{lead_id: company data or False}
        :raise: several errors, notably
          * InsufficientCreditError: {
            "credit": 4.0,
            "service_name": "reveal",
            "base_url": "https://iap.odoo.com/iap/1/credit",
            "message": "You don't have enough credits on your account to use this service."
            }
        """
        params = {
            'domains': lead_emails,
        }
        return self._contact_iap('/iap/clearbit/1/lead_enrichment_email', params=params)
