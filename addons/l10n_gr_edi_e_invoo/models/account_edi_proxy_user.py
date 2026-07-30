from stdnum.gr import vat as gr_vat

from odoo import fields, models
from odoo.exceptions import RedirectWarning


L10N_GR_EDI_DEFAULT_IAP_ENDPOINT = 'https://l10n-gr-edi.api.odoo.com'
L10N_GR_EDI_DEFAULT_IAP_TEST_ENDPOINT = 'https://l10n-gr-edi.test.odoo.com'
L10N_GR_EDI_IAP_ENDPOINT_PARAM = 'l10n_gr_edi.iap_endpoint'
L10N_GR_EDI_IAP_ROUTE_PREFIX = '/api/l10n_gr_edi/1'
L10N_GR_EDI_PROXY_TYPE = 'l10n_gr_edi'


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(
        selection_add=[(L10N_GR_EDI_PROXY_TYPE, 'Greek EDI')],
        ondelete={L10N_GR_EDI_PROXY_TYPE: 'cascade'},
    )

    _unique_identification_l10n_gr_edi = models.UniqueIndex(
        "(edi_identification, edi_mode) WHERE (active IS TRUE AND proxy_type = 'l10n_gr_edi')",
        "This EDI identification is already assigned to an active user.",
    )

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        endpoint_override = self.env['ir.config_parameter'].sudo().get_str(L10N_GR_EDI_IAP_ENDPOINT_PARAM)
        urls[L10N_GR_EDI_PROXY_TYPE] = {
            'prod': L10N_GR_EDI_DEFAULT_IAP_ENDPOINT,
            'test': (endpoint_override or L10N_GR_EDI_DEFAULT_IAP_TEST_ENDPOINT).rstrip('/'),
            'demo': False,
        }
        return urls

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type == L10N_GR_EDI_PROXY_TYPE:
            if not company.vat:
                raise RedirectWarning(
                    message=self.env._(
                        'Please fill the VAT number of company "%(company_name)s" before sending electronic invoices.',
                        company_name=company.display_name,
                    ),
                    action=company._get_records_action(),
                    button_text=self.env._("Go to company"),
                )
            return gr_vat.compact(company.vat)
        return super()._get_proxy_identification(company, proxy_type)

    def _l10n_gr_edi_proxy_request(self, route, params):
        self.ensure_one()
        return self._make_request(
            url=f"{self._get_server_url()}{L10N_GR_EDI_IAP_ROUTE_PREFIX}/{route}",
            params={**params, 'lang': self.env.lang},
        )
