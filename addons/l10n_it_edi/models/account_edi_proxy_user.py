# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Account_Edi_Proxy_ClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(selection_add=[('l10n_it_edi', 'Italian EDI')], ondelete={'l10n_it_edi': 'cascade'})

    _unique_identification_l10n_it_edi = models.UniqueIndex(
        "(edi_identification, proxy_type, edi_mode) WHERE (active AND proxy_type = 'l10n_it_edi')",
        "This edi identification is already assigned to an active user",
    )

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['l10n_it_edi'] = {
            'demo': False,
            'prod': 'https://l10n-it-edi.api.odoo.com',
            'test': 'https://iap-services-test.odoo.com',
        }
        return urls

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type == 'l10n_it_edi':
            if not company.l10n_it_codice_fiscale:
                raise UserError(_('Please fill your codice fiscale to be able to receive invoices from FatturaPA'))
            return company.partner_id._l10n_it_edi_normalized_codice_fiscale()
        return super()._get_proxy_identification(company, proxy_type)

    def _toggle_proxy_user_active(self):
        """
        Toggle the value of the ``active`` boolean field of the proxy_user,
        and handle sending the reactivate/deactivate requests to the IAP side.
        """
        self.ensure_one()
        server_url = self._get_proxy_urls()['l10n_it_edi'][self.edi_mode]

        if self.active:
            self._make_request(f"{server_url}/api/l10n_it_edi/1/deactivate_user")
        else:
            self._make_request(f"{server_url}/api/l10n_it_edi/1/reactivate_user")

        self.active = not self.active

    def _get_iap_params(self, company, proxy_type, private_key_sudo):
        iap_params = super()._get_iap_params(company, proxy_type, private_key_sudo)
        iap_params['l10n_it_vat'] = company.vat
        return iap_params

    def _register_proxy_user(self, company, proxy_type, edi_mode):
        if proxy_type == 'l10n_it_edi':
            company = company._l10n_it_get_edi_company()
        return super()._register_proxy_user(company, proxy_type, edi_mode)
