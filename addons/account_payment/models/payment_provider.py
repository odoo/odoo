# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class Paymentprovider(models.Model):
    _inherit = 'payment.provider'

    journal_id = fields.Many2one(
        string="Payment Journal",
        help="The journal in which the successful transactions are posted.",
        comodel_name='account.journal',
        compute='_compute_journal_id',
        inverse='_inverse_journal_id',
        domain='[("type", "=", "bank"), ("company_id", "=", company_id)]',
        copy=False,
    )

    #=== COMPUTE METHODS ===#

    @api.depends('code')
    def _compute_journal_id(self):
        for provider in self:
            payment_method = self.env['account.payment.method.line'].search([
                ('journal_id.company_id', '=', provider.company_id.id),
                ('code', '=', provider.code)
            ], limit=1)
            if payment_method:
                provider.journal_id = payment_method.journal_id
            else:
                provider.journal_id = False

    def _inverse_journal_id(self):
        for provider in self:
            payment_method_line = self.env['account.payment.method.line'].search([
                ('journal_id.company_id', '=', provider.company_id.id),
                ('code', '=', provider.code),
            ], limit=1)
            if provider.journal_id:
                if not payment_method_line:
                    default_payment_method_id = provider._get_default_payment_method_id(
                        provider.code
                    )
                    existing_payment_method_line = self.env['account.payment.method.line'].search([
                        ('payment_method_id', '=', default_payment_method_id),
                        ('journal_id', '=', provider.journal_id.id),
                    ], limit=1)
                    if not existing_payment_method_line:
                        self.env['account.payment.method.line'].create({
                            'payment_method_id': default_payment_method_id,
                            'journal_id': provider.journal_id.id,
                        })
                else:
                    payment_method_line.journal_id = provider.journal_id
            elif payment_method_line:
                payment_method_line.unlink()

    @api.model
    def _get_default_payment_method_id(self, code):
        provider_payment_method = self._get_provider_payment_method(code)
        if provider_payment_method:
            return provider_payment_method.id
        return self.env.ref('account.account_payment_method_manual_in').id

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

    def _check_existing_payment_method_lines(self, payment_method):
        existing_payment_method_lines_count =  \
            self.env['account.payment.method.line'].search_count([('payment_method_id', '=', \
                payment_method.id)], limit=1)
        return bool(existing_payment_method_lines_count)

    @api.model
    def _remove_provider(self, code):
        """ Override of `payment` to delete the payment method of the provider. """
        payment_method = self._get_provider_payment_method(code)
        if self._check_existing_payment_method_lines(payment_method):
            raise UserError(_("To uninstall this module, please remove first the corresponding payment method line in the incoming payments tab defined on the bank journal."))
        super()._remove_provider(code)
        payment_method.unlink()
