from odoo import models, fields, api, Command


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_latam_new_check_ids = fields.One2many('l10n_latam.payment.register.check', 'payment_register_id', string="Checks")

    l10n_latam_check_ids = fields.Many2many(
        comodel_name='l10n_latam.account.payment.check',
        string='Checks',
    )

    @api.depends('l10n_latam_new_check_ids', 'l10n_latam_new_check_ids.amount')
    def _compute_amount(self):
        super()._compute_amount()
        # TODO: filter by new_third_party_checks
        for wizard in self.filtered('l10n_latam_new_check_ids'):
            wizard.amount = sum(wizard.l10n_latam_new_check_ids.mapped('amount'))
        for wizard in self.filtered('l10n_latam_check_ids'):
            wizard.amount = sum(wizard.l10n_latam_check_ids.mapped('amount'))


    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        if self.l10n_latam_new_check_ids:
            vals.update({'l10n_latam_new_check_ids': [Command.create({
                'name': x.name,
                'l10n_latam_check_bank_id': x.l10n_latam_check_bank_id.id,
                'l10n_latam_check_issuer_vat': x.l10n_latam_check_issuer_vat,
                'l10n_latam_check_payment_date': x.l10n_latam_check_payment_date,
                'amount': x.amount}) for x in self.l10n_latam_new_check_ids
            ]})
        if self.l10n_latam_check_ids:
            vals.update({
                'l10n_latam_check_ids': [Command.link(x.id) for x in self.l10n_latam_check_ids]
            })
        return vals
