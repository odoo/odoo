# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(
        selection_add=[('l10n_it_edi', 'Italian EDI')],
    )

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['l10n_it_edi'] = {
            'prod': 'https://l10n-it-edi.api.odoo.com',
            'test': 'https://iap-services-test.odoo.com',
        }
        return urls

    def _compute_proxy_type(self):
        # Extends account_edi_proxy_client
        super()._compute_proxy_type()
        for user in self:
            if user.company_id.country_code == 'IT':
                user.proxy_type = 'l10n_it_edi'
