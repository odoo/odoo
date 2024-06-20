# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from werkzeug.urls import url_join

from odoo import _, fields, models
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    # ------------------
    # Fields declaration
    # ------------------

    proxy_type = fields.Selection(selection_add=[('l10n_my_edi', 'Malaysian EDI')], ondelete={'l10n_my_edi': 'cascade'})

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _get_proxy_urls(self):
        # EXTENDS 'account_edi_proxy_client'
        urls = super()._get_proxy_urls()
        # todo replace in later cycle.
        urls['l10n_my_edi'] = {
            'demo': False,
            'prod': 'http://localhost:8068',
            'test': 'http://localhost:8068',
        }
        return urls

    def _get_proxy_identification(self, company, proxy_type):
        # EXTENDS 'account_edi_proxy_client'
        if proxy_type == 'l10n_my_edi':
            if not company.vat:
                raise UserError(_('Please fill the TIN of company "%(company_name)s" before enabling the integration with MyInvois.',
                                  company_name=company.display_name))
            return company.vat
        return super()._get_proxy_identification(company, proxy_type)

    # ----------------
    # Business methods
    # ----------------

    def _l10n_my_edi_contact_proxy(self, endpoint, params):
        self.ensure_one()
        try:
            response = self._make_request(
                url=url_join(self._get_server_url(), endpoint),
                params=params,
            )
        except AccountEdiProxyError as _error:
            # Request error while contacting the IAP server. We assume it is a temporary error.
            raise UserError(_("Failed to contact the E-Invoicing service. Please try again later."))

        return response
