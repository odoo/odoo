# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    journal_id = fields.Many2one(
        string="Payment Journal",
        help="The journal in which the successful transactions are posted.",
        comodel_name='account.journal',
        check_company=True,
        domain='[("type", "=", "bank")]',
        copy=False,
    )

    account_payment_method_id = fields.Many2one(
        comodel_name='account.payment.method',
        compute='_compute_account_payment_method_id',
        store=True,
    )

    #=== COMPUTE METHODS ===#

    @api.depends('code', 'state', 'company_id')
    def _compute_journal_id(self):
        for provider in self:
            if not provider.journal_id:
                provider.journal_id = self.env['account.journal'].search(
                        [
                            ('company_id', '=', provider.company_id.id),
                            ('type', '=', 'bank'),
                        ],
                        limit=1,
                    )

    def _compute_account_payment_method_id(self):
        payment_methods = self.env['account.payment.method'].search([('code', 'in', self.mapped('code'))])
        for provider in self:
            provider.account_payment_method_id = payment_methods.filtered(lambda m: m.code == provider.code)

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        providers = super().create(vals_list)
        providers._compute_account_payment_method_id()
        return providers

    #=== BUSINESS METHODS ===#

    @api.model
    def _setup_provider(self, code):
        """ Override of `payment` to create the payment method of the provider. """
        super()._setup_provider(code)
        self._setup_payment_method(code)

    @api.model
    def _setup_payment_method(self, code):
        if code not in ('none', 'custom'):
            providers_description = dict(self._fields['code']._description_selection(self.env))
            self.env['account.payment.method'].sudo().create({
                'name': providers_description[code],
                'code': code,
                'payment_type': 'inbound',
            })
            self.env['payment.provider'].search([('code', '=', code)])._compute_account_payment_method_id()

    def _check_existing_payment(self, payment_method):
        existing_payment_count = self.env['account.payment'].search_count([('payment_method_id', '=', payment_method.id)], limit=1)
        return bool(existing_payment_count)

    @api.model
    def _remove_provider(self, code, **kwargs):
        """ Override of `payment` to delete the payment method of the provider. """
        # If the payment method is used by any payments, we block the uninstallation of the module.
        if self._check_existing_payment(self.account_payment_method_id):
            raise UserError(_("You cannot uninstall this module as payments using this payment method already exist."))
        super()._remove_provider(code, **kwargs)
        self.account_payment_method_id.unlink()
