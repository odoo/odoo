# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid
from urllib.parse import urlencode

from odoo import fields, models
from odoo.exceptions import UserError

from .baiwang_client import BaiwangClient


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_cn_edi_mode = fields.Selection(related="company_id.l10n_cn_edi_mode", readonly=False)
    l10n_cn_edi_company_vat = fields.Char(string="Company Tax ID", related="company_id.vat")
    l10n_cn_accept_processing = fields.Boolean()
    l10n_cn_baiwang_org_auth_code = fields.Char(related="company_id.l10n_cn_baiwang_org_auth_code", readonly=False)
    l10n_cn_baiwang_subscription_status = fields.Selection(
        related="company_id.l10n_cn_baiwang_subscription_status",
        readonly=True,
    )
    l10n_cn_baiwang_proxy_user_id = fields.Many2one(
        related='company_id.l10n_cn_baiwang_proxy_user_id',
        readonly=True,
    )

    # ----------------
    # Action methods
    # ----------------

    def action_l10n_cn_baiwang_test_connection(self):
        """Test Baiwang API connection by attempting OAuth token retrieval."""
        self.ensure_one()
        # Save pending changes first
        self.execute()
        client = BaiwangClient(self.company_id)
        client._get_token()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Connection Successful",
                'message': "Successfully authenticated with Baiwang API.",
                'type': 'success',
                'sticky': False,
            },
        }

    def action_open_company_form(self):
        """ This will be used to ease the configuration by allowing to quickly access the company. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_id': self.env.company.id,
            'res_model': 'res.company',
            'target': 'new',
            'view_mode': 'form',
        }

    def _l10n_cn_baiwang_get_iap_callback_url(self, callback_path, request_id=None):
        # 1. Look up the param directly using ORM search instead of get_param
        param = self.env['ir.config_parameter'].sudo().search([
            ('key', '=', 'web.base.url')  # (Or whichever key your code was originally checking here)
        ], limit=1)

        base_url = param.value if param else ''

        # (Keep the rest of your existing logic for building the URL below)
        url = f"{base_url.rstrip('/')}{callback_path}"
        if request_id:
            url = f"{url}?requestId={request_id}"
        return url

    def _l10n_cn_baiwang_build_external_url(self, base_url, company, callback_path, proxy_user=False):
        request_id = uuid.uuid4().hex
        callback_url = self._l10n_cn_baiwang_get_iap_callback_url(callback_path, request_id=request_id)
        query_values = {
            'taxNo': company.vat or '',
            'companyName': company.name or '',
            'callbackUrl': callback_url,
            'requestId': request_id,
        }
        if proxy_user:
            query_values['idClient'] = proxy_user.id_client
        query_string = urlencode(query_values)
        separator = '&' if '?' in base_url else '?'
        company.sudo().l10n_cn_baiwang_last_request_id = request_id
        return f"{base_url}{separator}{query_string}"

    def action_l10n_cn_baiwang_register_proxy_user(self):
        self.ensure_one()
        company = self.company_id
        if not company.vat:
            raise UserError(self.env._("Please set the company Tax ID before registering to the Baiwang proxy."))
        company._l10n_cn_baiwang_create_proxy_user()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._("Proxy user ready"),
                'message': self.env._("Baiwang proxy user registration is completed for this company."),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_l10n_cn_baiwang_subscribe(self):
        self.ensure_one()
        company = self.company_id
        if not company.vat:
            raise UserError(self.env._("Please set the company Tax ID before subscribing to Baiwang."))

        # Bypass Odoo's shifting get_param API by directly reading the database record
        param = self.env['ir.config_parameter'].sudo().search([
            ('key', '=', 'l10n_cn_baiwang.subscription_url')
        ], limit=1)
        subscribe_url = param.value if param else 'https://www-pre.baiwang.com'

        target_url = self._l10n_cn_baiwang_build_external_url(
            subscribe_url,
            company,
            '/l10n_cn_edi_baiwang/callback/order_complete',
            proxy_user=company.l10n_cn_baiwang_proxy_user_id,
        )
        return {
            'type': 'ir.actions.act_url',
            'url': target_url,
            'target': 'new',
        }

    def action_l10n_cn_baiwang_authorize(self):
        self.ensure_one()
        company = self.company_id
        if company.l10n_cn_baiwang_subscription_status == 'not_subscribed':
            raise UserError(self.env._("Please complete Baiwang subscription first."))
        authorize_url = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_cn_baiwang.authorization_url',
            default='https://www-pre.baiwang.com',
        )
        target_url = self._l10n_cn_baiwang_build_external_url(
            authorize_url,
            company,
            '/l10n_cn_edi_baiwang/callback/org_auth_code',
            proxy_user=company.l10n_cn_baiwang_proxy_user_id,
        )
        return {
            'type': 'ir.actions.act_url',
            'url': target_url,
            'target': 'new',
        }

    def action_l10n_cn_baiwang_sync_registration_status(self):
        self.ensure_one()
        company = self.company_id
        if not company.vat:
            raise UserError(self.env._("Please set the company Tax ID before connecting to Baiwang."))

        proxy_user = self.env['account_edi_proxy_client.user'].search([
            ('company_id', '=', company.id),
            ('proxy_type', '=', 'l10n_cn_edi_baiwang'),
        ], limit=1)

        if not proxy_user:
            company._l10n_cn_baiwang_create_proxy_user()

        params = {'tax_no': company.vat}
        if company.l10n_cn_baiwang_last_request_id:
            params['baiwang_request_id'] = company.l10n_cn_baiwang_last_request_id
        response = proxy_user._l10n_cn_baiwang_contact_proxy(
            endpoint='api/l10n_cn_edi_baiwang/1/get_registration_state',
            params=params,
        )
        if not response or not response.get('success'):
            raise UserError(self.env._("Could not sync registration status from Baiwang proxy."))

        values = {}
        if status := response.get('subscription_status'):
            values['l10n_cn_baiwang_subscription_status'] = status
        if org_auth_code := response.get('org_auth_code'):
            values['l10n_cn_baiwang_org_auth_code'] = org_auth_code
            values['l10n_cn_baiwang_subscription_status'] = 'authorized'

        if values:
            company.sudo().write(values)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._("Sync complete"),
                'message': self.env._("Registration status has been synchronized from the Baiwang proxy."),
                'type': 'success',
                'sticky': False,
            },
        }
