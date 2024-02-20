from odoo import models, fields, api, Command


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    l10n_latam_new_check_ids = fields.One2many('l10n_latam.payment.register.check', 'payment_register_id', string="Checks")

    # l10n_latam_check_id = fields.Many2one(
    #     comodel_name='account.payment',
    #     string='Check',
    # )
    # l10n_latam_check_bank_id = fields.Many2one(
    #     comodel_name='res.bank',
    #     string='Check Bank',
    #     compute='_compute_l10n_latam_check_bank_id', store=True, readonly=False,
    # )
    # l10n_latam_check_issuer_vat = fields.Char(
    #     string='Check Issuer VAT',
    #     compute='_compute_l10n_latam_check_issuer_vat', store=True, readonly=False,
    # )
    # l10n_latam_check_number = fields.Char(
    #     string="Check Number",
    # )
    # l10n_latam_manual_checks = fields.Boolean(
    #     related='journal_id.l10n_latam_manual_checks',
    # )
    # l10n_latam_check_payment_date = fields.Date(
    #     string='Check Cash-In Date', help="Date from when you can cash in the check, turn the check into cash",
    # )

    # @api.depends('payment_method_line_id.code', 'partner_id')
    # def _compute_l10n_latam_check_bank_id(self):
    #     new_third_party_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_party_checks')
    #     for rec in new_third_party_checks:
    #         rec.l10n_latam_check_bank_id = rec.partner_id.bank_ids[:1].bank_id
    #     (self - new_third_party_checks).l10n_latam_check_bank_id = False

    # @api.depends('payment_method_line_id.code', 'partner_id')
    # def _compute_l10n_latam_check_issuer_vat(self):
    #     new_third_party_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_party_checks')
    #     for rec in new_third_party_checks:
    #         rec.l10n_latam_check_issuer_vat = rec.partner_id.vat
    #     (self - new_third_party_checks).l10n_latam_check_issuer_vat = False

    @api.depends('l10n_latam_new_check_ids')
    def _compute_amount(self):
        super()._compute_amount()
        # TODO: filter by new_third_party_checks
        for wizard in self.filtered('l10n_latam_new_check_ids'):
            wizard.amount = sum(wizard.l10n_latam_new_check_ids.mapped('amount'))

    # @api.depends('l10n_latam_check_id')
    # def _compute_currency_id(self):
    #     super()._compute_currency_id()
    #     for wizard in self.filtered('l10n_latam_check_id'):
    #         wizard.currency_id = wizard.l10n_latam_check_id.currency_id

    @api.onchange('payment_method_line_id', 'journal_id')
    def _onchange_to_reset_check_ids(self):
        # If any of these fields change, the domain of the selectable checks could change
        self.l10n_latam_check_ids = False

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        l10n_latam_check_ids = [{
            'name': x.name,
            'l10n_latam_check_bank_id': x.l10n_latam_check_bank_id.id,
            'l10n_latam_check_issuer_vat': x.l10n_latam_check_issuer_vat,
            'l10n_latam_check_payment_date': x.l10n_latam_check_payment_date,
            'amount': x.amount} for x in self.l10n_latam_new_check_ids
        ]
        if l10n_latam_check_ids:
            vals.update({
                'l10n_latam_check_ids': [Command.create(l10n_latam_check_ids)]
            })
        # vals.update({
        #     'l10n_latam_check_id': self.l10n_latam_check_id.id,
        #     'l10n_latam_check_bank_id': self.l10n_latam_check_bank_id.id,
        #     'l10n_latam_check_issuer_vat': self.l10n_latam_check_issuer_vat,
        #     'check_number': self.l10n_latam_check_number,
        #     'l10n_latam_check_payment_date': self.l10n_latam_check_payment_date,
        # })
        return vals
