from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_latam_new_check_ids = fields.One2many('l10n_latam.payment.register.check', 'payment_register_id', string="New Checks")
    l10n_latam_move_check_ids = fields.Many2many(
        comodel_name='l10n_latam.check',
        string='Checks',
    )

    @api.depends('l10n_latam_move_check_ids.amount', 'l10n_latam_new_check_ids.amount', 'payment_method_code')
    def _compute_amount(self):
        super()._compute_amount()
        for wizard in self.filtered(lambda x: x._is_latam_check_payment(check_subtype='new_check')):
            wizard.amount = sum(wizard.l10n_latam_new_check_ids.mapped('amount'))
        for wizard in self.filtered(lambda x: x._is_latam_check_payment(check_subtype='move_check')):
            wizard.amount = sum(wizard.l10n_latam_move_check_ids.mapped('amount'))

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
        if self.l10n_latam_new_check_ids:
            vals.update({'l10n_latam_new_check_ids': [Command.create({
                'name': x.name,
                'bank_id': x.bank_id.id,
                'issuer_vat': x.issuer_vat,
                'payment_date': x.payment_date,
                'amount': x.amount}) for x in self.l10n_latam_new_check_ids
            ]})
        if self.l10n_latam_move_check_ids:
            vals.update({
                'l10n_latam_move_check_ids': [Command.link(x.id) for x in self.l10n_latam_move_check_ids]
            })
        return vals

    def action_create_payments(self):
        if self._is_latam_check_payment(check_subtype="move_check"):
            latam_check_currencies = self.l10n_latam_move_check_ids.mapped("currency_id")
            if latam_check_currencies and (len(latam_check_currencies) > 1 or latam_check_currencies != self.currency_id):
                raise ValidationError(_(
                    "You can't mix checks of different currencies in one payment, "
                    "and you can't change the payment's currency if checks are already created in that currency.\n"
                    "Please create separate payments for each currency."
                ))
        return super().action_create_payments()
