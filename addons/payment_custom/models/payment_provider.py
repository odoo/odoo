# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.fields import Domain

from odoo.addons.payment_custom import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    _custom_providers_setup = models.Constraint(
        "CHECK(custom_mode IS NULL OR (code = 'custom' AND custom_mode IS NOT NULL))",
        'Only custom providers should have a custom mode.',
    )

    code = fields.Selection(
        selection_add=[('custom', "Custom")], ondelete={'custom': 'set default'}
    )
    custom_mode = fields.Selection(
        string="Custom Mode",
        selection=[('wire_transfer', "Wire Transfer")],
        required_if_provider='custom',
    )
    qr_code = fields.Boolean(
        string="Enable QR Codes", help="Enable the use of QR-codes when paying by wire transfer.")
    company_partner_id = fields.Many2one(
        'res.partner',
        related='company_id.partner_id',
        store=False,
    )
    bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='Bank Account',
        domain="[('partner_id', '=', company_partner_id)]",
        copy=False,
    )

    # === CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        providers = super().create(vals_list)
        providers.filtered(lambda p: p.custom_mode == 'wire_transfer').pending_msg = None
        return providers

    def write(self, vals):
        res = super().write(vals)
        if 'bank_account_id' in vals:
            for provider in self.filtered(lambda p: p.custom_mode == 'wire_transfer'):
                provider._recompute_pending_msg()
        return res

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        self.ensure_one()
        if self.code != 'custom' or self.custom_mode != 'wire_transfer':
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS ===#

    def _get_pending_msg_bank_account(self):
        return self.bank_account_id

    def _recompute_pending_msg(self):
        account = self._get_pending_msg_bank_account()
        account_details = (
            f'<div class="mt-3"><b>{self.env._("Beneficiary")}: </b><span class="user-select-all border rounded bg-light p-2">{account.holder_name}</span></div>'
            f'<div class="mt-3"><b>{self.env._("Bank Account")}: </b><span class="user-select-all border rounded bg-light p-2">{account.display_name}</span></div>'
        ) if account else ''

        self.pending_msg = (
            f'<div>'
            f'<h5>{self.env._("Your order will be confirmed after payment is received.")}</h5>'
            f'{account_details}'
            f'</div>'
        )

    # === SETUP METHODS === #

    @api.model
    def _get_provider_domain(self, provider_code, *, custom_mode='', **kwargs):
        res = super()._get_provider_domain(provider_code, custom_mode=custom_mode, **kwargs)
        if provider_code == 'custom' and custom_mode:
            return Domain.AND([res, [('custom_mode', '=', custom_mode)]])
        return res

    @api.model
    def _get_removal_values(self):
        """ Override of `payment` to nullify the `custom_mode` field. """
        res = super()._get_removal_values()
        res['custom_mode'] = None
        return res
