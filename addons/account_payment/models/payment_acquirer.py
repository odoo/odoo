# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    journal_id = fields.Many2one(
        string="Payment Journal",
        help="The journal in which the successful transactions are posted.",
        comodel_name='account.journal',
        compute='_compute_journal_id',
        inverse='_inverse_journal_id',
        domain='[("type", "=", "bank"), ("company_id", "=", company_id)]',
    )

    #=== COMPUTE METHODS ===#

    @api.depends('provider')
    def _compute_journal_id(self):
        for acquirer in self:
            payment_method = self.env['account.payment.method.line'].search([
                ('journal_id.company_id', '=', acquirer.company_id.id),
                ('code', '=', acquirer.provider)
            ], limit=1)
            if payment_method:
                acquirer.journal_id = payment_method.journal_id
            else:
                acquirer.journal_id = False

    def _inverse_journal_id(self):
        for acquirer in self:
            payment_method_line = self.env['account.payment.method.line'].search([
                ('journal_id.company_id', '=', acquirer.company_id.id),
                ('code', '=', acquirer.provider),
            ], limit=1)
            if acquirer.journal_id:
                if not payment_method_line:
                    default_payment_method_id = acquirer._get_default_payment_method_id(
                        acquirer.provider
                    )
                    existing_payment_method_line = self.env['account.payment.method.line'].search([
                        ('payment_method_id', '=', default_payment_method_id),
                        ('journal_id', '=', acquirer.journal_id.id),
                    ], limit=1)
                    if not existing_payment_method_line:
                        self.env['account.payment.method.line'].create({
                            'payment_method_id': default_payment_method_id,
                            'journal_id': acquirer.journal_id.id,
                        })
                else:
                    payment_method_line.journal_id = acquirer.journal_id
            elif payment_method_line:
                payment_method_line.unlink()

    @api.model
    def _get_default_payment_method_id(self, provider):
        provider_payment_method = self._get_provider_payment_method(provider)
        if provider_payment_method:
            return provider_payment_method.id
        return self.env.ref('account.account_payment_method_manual_in').id

    @api.model
    def _get_provider_payment_method(self, provider):
        return self.env['account.payment.method'].search([('code', '=', provider)], limit=1)

    #=== BUSINESS METHODS ===#

    @api.model
    def _setup_provider(self, provider_code):
        """ Override of `payment` to create the payment method of the provider. """
        super()._setup_provider(provider_code)
        self._setup_payment_method(provider_code)

    @api.model
    def _setup_payment_method(self, provider):
        if provider not in ('none', 'transfer') and not self._get_provider_payment_method(provider):
            providers_description = dict(self._fields['provider']._description_selection(self.env))
            self.env['account.payment.method'].create({
                'name': providers_description[provider],
                'code': provider,
                'payment_type': 'inbound',
            })

    @api.model
    def _remove_provider(self, provider):
        """ Override of `payment` to delete the payment method of the provider. """
        super()._remove_provider(provider)
        self._get_provider_payment_method(provider).unlink()
