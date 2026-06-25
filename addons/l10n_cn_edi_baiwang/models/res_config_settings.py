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

    def action_l10n_cn_baiwang_subscribe(self):
        self.ensure_one()
        if not self.company_id.vat:
            raise UserError(self.env._("Please set the company Tax ID before subscribing to Baiwang."))

        return {
            'type': 'ir.actions.act_url',
            'url': self._l10n_cn_baiwang_get_route_url('subscribe', '/l10n_cn_edi_baiwang/callback/order_complete'),
            'target': 'new',
        }

    def action_l10n_cn_baiwang_authorize(self):
        self.ensure_one()
        if self.company_id.l10n_cn_baiwang_subscription_status == 'not_subscribed':
            raise UserError(self.env._("Please complete Baiwang subscription first."))

        return {
            'type': 'ir.actions.act_url',
            'url': self._l10n_cn_baiwang_get_route_url('authorize', '/l10n_cn_edi_baiwang/callback/org_auth_code'),
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

    def _l10n_cn_baiwang_get_route_url(self, action, callback_path):
        proxy_user = self.company_id._l10n_cn_baiwang_create_proxy_user()
        proxy_url = proxy_user._get_server_url().rstrip('/')
        request_id = uuid.uuid4().hex
        self.company_id.sudo().l10n_cn_baiwang_last_request_id = request_id

        params = urlencode({
            'taxNo': self.company_id.vat or '',
            'companyName': self.company_id.name or '',
            'callbackUrl': f"{proxy_url}{callback_path}?requestId={request_id}",
            'requestId': request_id,
            'idClient': proxy_user.id_client,
            'environment': self.company_id.l10n_cn_edi_mode,
        })
        return f"{proxy_url}/api/l10n_cn_edi_baiwang/1/route/{action}?{params}"
