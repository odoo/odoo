# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.exceptions import UserError


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(selection_add=[('pdp', 'French PDP')], ondelete={'pdp': 'cascade'})

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        config = self.env['ir.config_parameter'].sudo()
        urls['pdp'] = {
            'demo': False,
            'prod': config.get_param('l10n_fr_pdp_proxy_server_url_prod', 'https://pdp.api.odoo.com'),
            'test': config.get_param('l10n_fr_pdp_proxy_server_url_test', 'https://pdp.test.odoo.com'),
        }
        return urls

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type == 'pdp':
            vat = company.partner_id.vat
            if not vat:
                raise UserError(_("Please set the company VAT before enabling PDP proxy integration."))
            return vat
        return super()._get_proxy_identification(company, proxy_type)

    def _l10n_fr_pdp_call_proxy(self, endpoint, params=None):
        self.ensure_one()
        if self.proxy_type != 'pdp':
            raise UserError(_("EDI user should be of type PDP."))
        try:
            server_url = (self._get_server_url() or '').rstrip('/')
            endpoint_url = '/%s' % (endpoint or '').lstrip('/')
            return self._make_request('%s%s' % (server_url, endpoint_url), params=params or {})
        except AccountEdiProxyError as error:
            raise UserError(error.message or _("Failed to contact the PDP proxy."))
