# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    journal_id = fields.Many2one(
        string="Payment Journal",
        help="The journal in which the successful transactions are posted.",
        comodel_name='account.journal',
        compute='_compute_journal_id',
        inverse='_inverse_journal_id',
        check_company=True,
        domain='[("type", "=", "bank")]',
        copy=False,
    )

    #=== COMPUTE METHODS ===#

    def _ensure_payment_method_line(self, allow_create=True):
        self.ensure_one()
        if not self.id:
            return

        default_payment_method = self._get_provider_payment_method(self._get_code())
        if not default_payment_method:
            return

        pay_method_line = self.env['account.payment.method.line'].search([
            ('payment_provider_id', '=', self.id),
            ('journal_id', '!=', False),
        ], limit=1)

        if not self.journal_id:
            if pay_method_line:
                pay_method_line.unlink()
                return

        if not pay_method_line:
            pay_method_line = self.env['account.payment.method.line'].search(
                [
                    *self.env['account.payment.method.line']._check_company_domain(self.company_id),
                    ('code', '=', self._get_code()),
                    ('payment_provider_id', '=', False),
                    ('journal_id', '!=', False),
                ],
                limit=1,
            )
        if pay_method_line:
            pay_method_line.payment_provider_id = self
            pay_method_line.journal_id = self.journal_id
            pay_method_line.name = self.name
        elif allow_create:
            create_values = {
                'name': self.name,
                'payment_method_id': default_payment_method.id,
                'journal_id': self.journal_id.id,
                'payment_provider_id': self.id,
            }
            pay_method_line_same_code = self.env['account.payment.method.line'].search(
                [
                    *self.env['account.payment.method.line']._check_company_domain(self.company_id),
                    ('code', '=', self._get_code()),
                ],
                limit=1,
            )
            if pay_method_line_same_code:
                create_values['payment_account_id'] = pay_method_line_same_code.payment_account_id.id
            self.env['account.payment.method.line'].create(create_values)

    @api.depends('code', 'state', 'company_id')
    def _compute_journal_id(self):
        for provider in self:
            pay_method_line = self.env['account.payment.method.line'].search([
                ('payment_provider_id', '=', provider._origin.id),
                ('journal_id', '!=', False),
            ], limit=1)

            if pay_method_line:
                provider.journal_id = pay_method_line.journal_id
            elif provider.state in ('enabled', 'test'):
                provider.journal_id = self.env['account.journal'].search(
                    [
                        ('company_id', '=', provider.company_id.id),
                        ('type', '=', 'bank'),
                    ],
                    limit=1,
                )
                if provider.id:
                    provider._ensure_payment_method_line()

    def _inverse_journal_id(self):
        for provider in self:
            provider._ensure_payment_method_line()

    @api.model
    def _get_provider_payment_method(self, code):
        return self.env['account.payment.method'].search([('code', '=', code)], limit=1)

    #=== BUSINESS METHODS ===#

    @api.model
    def _setup_provider(self, code):
        """ Override of `payment` to create the payment method of the provider. """
        super()._setup_provider(code)
        self._setup_payment_method(code)

    @api.model
    def _setup_payment_method(self, code):
        if code not in ('none', 'custom') and not self._get_provider_payment_method(code):
            providers_description = dict(self._fields['code']._description_selection(self.env))
            self.env['account.payment.method'].sudo().create({
                'name': providers_description[code],
                'code': code,
                'payment_type': 'inbound',
            })

    def _check_existing_payment(self, payment_method):
        existing_payment_count = self.env['account.payment'].search_count([('payment_method_id', '=', payment_method.id)], limit=1)
        return bool(existing_payment_count)

    @api.model
    def _remove_provider(self, code):
        """ Override of `payment` to delete the payment method of the provider. """
        payment_method = self._get_provider_payment_method(code)
        # If the payment method is used by any payments, we block the uninstallation of the module.
        if self._check_existing_payment(payment_method):
            raise UserError(_("You cannot uninstall this module as payments using this payment method already exist."))
        super()._remove_provider(code)
        payment_method.unlink()
