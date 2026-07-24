# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.urls import urljoin as url_join

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import (
    AccountEdiProxyError,
)


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(selection_add=[('l10n_cn_edi_baiwang', 'Baiwang EDI')], ondelete={'l10n_cn_edi_baiwang': 'cascade'})

    _unique_identification_l10n_cn_edi_baiwang = models.UniqueIndex(
        "(edi_identification, proxy_type, edi_mode) WHERE (active AND proxy_type = 'l10n_cn_edi_baiwang')",
        "This EDI identification is already assigned to an active Baiwang user",
    )

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()

        # Look for a local dev override, otherwise default to Odoo's real test server
        param = self.env['ir.config_parameter'].sudo().search([
            ('key', '=', 'l10n_cn_baiwang.local_proxy_url'),
        ], limit=1)

        test_url = param.value if param else 'https://iap-services-test.odoo.com'

        urls['l10n_cn_edi_baiwang'] = {
            'demo': 'demo',
            'prod': 'https://iap.odoo.com',
            'test': test_url,
        }
        return urls

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type == 'l10n_cn_edi_baiwang':
            if not company.vat:
                raise UserError(company.env._('Please set the company Tax ID before enabling Baiwang EDI proxy access.'))
            return company.vat
        return super()._get_proxy_identification(company, proxy_type)

    def _l10n_cn_baiwang_contact_proxy(self, endpoint, params):
        self.ensure_one()
        try:
            return self._make_request(
                url=url_join(self._get_server_url(), endpoint),
                params=params,
            )
        except AccountEdiProxyError as _error:
            raise UserError(self.env._('Failed to contact the Baiwang proxy service. Please try again later.'))

    def _l10n_cn_baiwang_call_proxy_endpoint(self, company, endpoint, **params):
        self.ensure_one()
        if self.proxy_type != 'l10n_cn_edi_baiwang':
            raise UserError(self.env._('This proxy user is not configured for Baiwang.'))
        return self._l10n_cn_baiwang_contact_proxy(endpoint=endpoint, params={
            'tax_no': company.vat,
            'environment': company.l10n_cn_edi_mode or 'test',
            **params,
        })

    # --- Baiwang Business Call Wrappers ---

    def _l10n_cn_baiwang_issue_invoice(self, company, invoice_data):
        return self._l10n_cn_baiwang_call_proxy_endpoint(
            company,
            endpoint='api/l10n_cn_edi_baiwang/1/issue_invoice',
            payload=invoice_data,
        )

    def _l10n_cn_baiwang_query_invoice(self, company, query_data):
        return self._l10n_cn_baiwang_call_proxy_endpoint(
            company,
            endpoint='api/l10n_cn_edi_baiwang/1/query_invoice',
            payload=query_data,
        )

    def _l10n_cn_baiwang_submit_red_form(self, company, red_form_data):
        return self._l10n_cn_baiwang_call_proxy_endpoint(
            company,
            endpoint='api/l10n_cn_edi_baiwang/1/submit_red_form',
            payload=red_form_data,
        )

    def _l10n_cn_baiwang_query_red_form(self, company, red_confirm_uuid):
        return self._l10n_cn_baiwang_call_proxy_endpoint(
            company,
            endpoint='api/l10n_cn_edi_baiwang/1/query_red_form',
            red_confirm_uuid=red_confirm_uuid,
        )

    def _l10n_cn_baiwang_poll_red_form_list(self, company, filters=None):
        return self._l10n_cn_baiwang_call_proxy_endpoint(
            company,
            endpoint='api/l10n_cn_edi_baiwang/1/poll_red_form_list',
            filters=filters or {},
        )

    def _l10n_cn_baiwang_operate_red_form(self, company, red_confirm_uuid, red_confirm_no, confirm_type):
        return self._l10n_cn_baiwang_call_proxy_endpoint(
            company,
            endpoint='api/l10n_cn_edi_baiwang/1/operate_red_form',
            red_confirm_uuid=red_confirm_uuid,
            red_confirm_no=red_confirm_no,
            confirm_type=confirm_type,
        )
