# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError

class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _get_server_url(self, edi_operating_mode=False):
        """ Return the base server URL for each operating mode. """
        urls = {
            'test': 'https://iap-services-test.odoo.com',
            'prod': 'https://l10n-it-edi.api.odoo.com',
        }
        return urls.get(edi_operating_mode or self.edi_operating_mode, False)

    def _retrieve_edi_identification(self, edi_format_code, company):
        if edi_format_code != 'fattura_pa':
            return super()._get_edi_identification(edi_format_code, company)
        edi_identification = company.partner_id._l10n_it_normalize_codice_fiscale(company.partner_id.l10n_it_codice_fiscale)
        if not edi_identification:
            raise UserError(_('Please fill your codice fiscale to be able to receive invoices from FatturaPA'))
        return edi_identification
