# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_cn_edi_mode = fields.Selection(related="company_id.l10n_cn_edi_mode", readonly=False)
    l10n_cn_edi_company_vat = fields.Char(string="Company Tax ID", related="company_id.vat")
    l10n_cn_baiwang_org_auth_code = fields.Char(related="company_id.l10n_cn_baiwang_org_auth_code", readonly=False)
    l10n_cn_baiwang_drawer = fields.Char(related="company_id.l10n_cn_baiwang_drawer", readonly=False)
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

    def action_l10n_cn_baiwang_subscribe(self):
        self.ensure_one()
        if not self.company_id.vat:
            raise UserError(self.env._("Please set the company Tax ID before subscribing to Baiwang."))

        response = self.company_id._l10n_cn_baiwang_create_proxy_user()._l10n_cn_baiwang_contact_proxy(
            endpoint='api/l10n_cn_edi_baiwang/1/route/subscribe',
            params={},
        )
        if not response.get('url'):
            raise UserError(self.env._("Could not retrieve the Baiwang subscription URL."))
        return {
            'type': 'ir.actions.act_url',
            'url': response['url'],
            'target': 'new',
        }

    def action_l10n_cn_baiwang_authorize(self):
        self.ensure_one()
        if self.company_id.l10n_cn_baiwang_subscription_status == 'not_subscribed':
            raise UserError(self.env._("Please complete Baiwang subscription first."))

        response = self.company_id._l10n_cn_baiwang_create_proxy_user()._l10n_cn_baiwang_contact_proxy(
            endpoint='api/l10n_cn_edi_baiwang/1/route/authorize',
            params={},
        )
        if not response.get('url'):
            raise UserError(self.env._("Could not retrieve the Baiwang authorization URL."))
        return {
            'type': 'ir.actions.act_url',
            'url': response['url'],
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
        ], limit=1) or company._l10n_cn_baiwang_create_proxy_user()
        params = {'tax_no': company.vat}
        if company.l10n_cn_baiwang_subscription_request_id:
            params['subscription_request_id'] = company.l10n_cn_baiwang_subscription_request_id
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
        if values:
            company.sudo().write(values)

    def action_open_company_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_id': self.company_id.id,
            'res_model': 'res.company',
            'target': 'new',
            'view_mode': 'form',
        }
