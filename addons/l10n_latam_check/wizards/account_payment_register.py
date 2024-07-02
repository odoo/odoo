from odoo import models, fields, api, Command


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

    def _is_latam_check_payment(self, check_subtype=False):
        if check_subtype == 'move_check':
            codes = ['in_third_party_checks', 'out_third_party_checks']
        elif check_subtype == 'new_check':
            codes = ['new_third_party_checks', 'own_checks']
        else:
            codes = ['in_third_party_checks', 'out_third_party_checks', 'new_third_party_checks', 'own_checks']
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
