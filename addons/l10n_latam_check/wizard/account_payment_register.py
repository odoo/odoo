from odoo import models, fields, api, Command
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_latam_new_check_ids = fields.One2many('l10n_latam.payment.register.check', 'payment_register_id', string="New Checks")
    l10n_latam_move_check_ids = fields.Many2many(
        comodel_name='l10n_latam.check',
        string='Checks',
    )
    l10n_latam_checks_amount = fields.Monetary(
        string="Checks Amount",
        currency_field='currency_id',
        compute='_compute_l10n_latam_checks_amount',
    )

    @api.depends('l10n_latam_new_check_ids.amount', 'l10n_latam_move_check_ids.amount', 'payment_method_code')
    def _compute_l10n_latam_checks_amount(self):
        for wizard in self:
            if wizard._is_latam_check_payment(check_subtype='new_check'):
                wizard.l10n_latam_checks_amount = sum(wizard.l10n_latam_new_check_ids.mapped('amount'))
            elif wizard._is_latam_check_payment(check_subtype='move_check'):
                wizard.l10n_latam_checks_amount = sum(wizard.l10n_latam_move_check_ids.mapped('amount'))
            else:
                wizard.l10n_latam_checks_amount = 0.0

    @api.depends('l10n_latam_checks_amount', 'payment_method_code')
    def _compute_amount(self):
        super()._compute_amount()
        for wizard in self.filtered(lambda x: x._is_latam_check_payment()):
            wizard.amount = wizard.l10n_latam_checks_amount

    @api.depends('l10n_latam_move_check_ids.currency_id')
    def _compute_currency_id(self):
        super()._compute_currency_id()
        for wizard in self.filtered(lambda x: x._is_latam_check_payment(check_subtype='move_check')):
            if wizard.l10n_latam_move_check_ids:
                wizard.currency_id = wizard.l10n_latam_move_check_ids[0].currency_id

    def _is_latam_check_payment(self, check_subtype=False):
        if check_subtype == 'move_check':
            codes = ['in_third_party_checks', 'out_third_party_checks', 'return_third_party_checks']
        elif check_subtype == 'new_check':
            codes = ['new_third_party_checks', 'own_checks']
        else:
            codes = ['in_third_party_checks', 'out_third_party_checks', 'return_third_party_checks', 'new_third_party_checks', 'own_checks']
        return self.payment_method_code in codes

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        if not self._is_latam_check_payment():
            return vals

        if self.l10n_latam_new_check_ids:
            vals.update({'l10n_latam_new_check_ids': [Command.create({
                'name': x.name,
                'issuer_vat': x.issuer_vat,
                'bank_account_id': x.bank_account_id.id,
                'payment_date': x.payment_date,
                'amount': x.amount}) for x in self.l10n_latam_new_check_ids
            ]})
        if self.l10n_latam_move_check_ids:
            vals.update({
                'l10n_latam_move_check_ids': [Command.link(x.id) for x in self.l10n_latam_move_check_ids]
            })
        return vals

    def action_create_payments(self):
        if self._is_latam_check_payment():
            if self._is_latam_check_payment(check_subtype="new_check") and not self.l10n_latam_new_check_ids:
                raise UserError(self.env._("Please add at least one check to create a payment with a check payment method."))
            if self._is_latam_check_payment(check_subtype="move_check") and not self.l10n_latam_move_check_ids:
                raise UserError(self.env._("Please select at least one check to create a payment with a check payment method."))
            latam_check_currencies = self.l10n_latam_move_check_ids.mapped("currency_id")
            if latam_check_currencies and (len(latam_check_currencies) > 1 or latam_check_currencies != self.currency_id):
                raise UserError(self.env._(
                    "You can't mix checks of different currencies in one payment, "
                    "and you can't change the payment's currency if checks are already created in that currency.\n"
                    "Please create separate payments for each currency."
                ))
        return super().action_create_payments()
