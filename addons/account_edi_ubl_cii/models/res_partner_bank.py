# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    acc_holder_partner_id = fields.Many2one(
        'res.partner',
        string='Factoring Payee',
        check_company=True,
        help='Structured third party for EN16931 BG-10 Payee when payment goes to someone '
             'other than the bank account owner. Used to export PayeeParty / PayeeTradeParty.',
    )
    is_factoring = fields.Boolean(
        string='Factoring',
        help='When set, exported e-invoices use factored document types (393/396) '
             'and payee role code DL on the payee party.',
    )
    payment_note = fields.Char(
        string='Payment Note',
        help='Optional note exported on electronic invoices when this bank account is used.',
    )

    @api.onchange('acc_holder_partner_id')
    def _onchange_acc_holder_partner_id(self):
        if self.acc_holder_partner_id:
            self.acc_holder_name = self.acc_holder_partner_id.name

    @api.depends('partner_id', 'acc_holder_partner_id')
    def _compute_account_holder_name(self):
        super()._compute_account_holder_name()
        for bank in self:
            if bank.acc_holder_partner_id:
                bank.acc_holder_name = bank.acc_holder_partner_id.name

    def _get_edi_payee_partner(self):
        self.ensure_one()
        if self.acc_holder_partner_id:
            return self.acc_holder_partner_id.commercial_partner_id
        return self.env['res.partner']

    def _get_edi_payee_account_holder_name(self):
        """Return BT-85 account holder name for e-invoice export."""
        self.ensure_one()
        if not self.acc_holder_partner_id:
            return False
        return self.acc_holder_name or self.acc_holder_partner_id.name

    def _get_edi_payee_role_code(self):
        self.ensure_one()
        if self.is_factoring:
            return 'DL'
        return False

    @api.constrains('is_factoring', 'acc_holder_partner_id')
    def _check_factoring_payee_partner(self):
        for bank in self:
            if bank.is_factoring and not bank.acc_holder_partner_id:
                raise ValidationError(_(
                    'A factoring bank account requires a payee partner for BG-10 export.',
                ))
