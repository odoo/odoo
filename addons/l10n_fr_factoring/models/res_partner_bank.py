# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    acc_holder_partner_id = fields.Many2one(
        'res.partner',
        string='Factor',
        check_company=True,
        help="Factor that holds this bank account. Exported as PayeeParty / "
             "PayeeTradeParty only when Factoring is set on this account.",
    )
    is_factoring = fields.Boolean(
        string='Factoring',
        help="This company bank account is a factoring IBAN. E-invoices that use it "
             "export document type 393 (invoice) or 396 (credit note) and payee role DL.",
    )
    payment_note = fields.Char(
        string='Payment Note',
        help="Optional payment instruction exported on e-invoices that use this factoring account.",
    )

    @api.onchange('acc_holder_partner_id', 'is_factoring')
    def _onchange_factoring_account_holder(self):
        if self.is_factoring and self.acc_holder_partner_id:
            self.acc_holder_name = self.acc_holder_partner_id.name

    @api.depends('partner_id', 'acc_holder_partner_id', 'is_factoring')
    def _compute_account_holder_name(self):
        super()._compute_account_holder_name()
        for bank in self:
            if bank.is_factoring and bank.acc_holder_partner_id:
                bank.acc_holder_name = bank.acc_holder_partner_id.name

    @api.constrains('is_factoring', 'acc_holder_partner_id')
    def _check_factoring_payee_partner(self):
        for bank in self:
            if bank.is_factoring and not bank.acc_holder_partner_id:
                raise ValidationError(_(
                    "A factoring bank account requires the factor that holds the account.",
                ))

    def _edi_is_factoring_bank(self):
        self.ensure_one()
        return bool(self.is_factoring and self.acc_holder_partner_id)

    def _get_edi_payee_partner(self):
        self.ensure_one()
        if not self._edi_is_factoring_bank():
            return self.env['res.partner']
        return self.acc_holder_partner_id.commercial_partner_id

    def _get_edi_payee_account_holder_name(self):
        self.ensure_one()
        if not self._edi_is_factoring_bank():
            return False
        return self.acc_holder_name or self.acc_holder_partner_id.name

    def _get_edi_payee_role_code(self):
        self.ensure_one()
        if self._edi_is_factoring_bank():
            return 'DL'
        return False

    def _edi_get_payment_note(self):
        self.ensure_one()
        if not self._edi_is_factoring_bank():
            return False
        return self.payment_note or False
