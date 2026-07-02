from odoo import api, fields, models

from odoo.exceptions import ValidationError


class L10nCnBalanceDeduction(models.Model):
    _name = 'l10n_cn.balance.deduction'
    _description = 'Balance Deduction Information'

    move_line_id = fields.Many2one(comodel_name='account.move.line', required=True, ondelete='cascade')

    voucher_type = fields.Selection(
        selection=[
            ('10', 'Special VAT Fapiao'),
            ('11', 'General VAT Fapiao'),
            ('12', 'Customs Import VAT Special Payment Receipt'),
            ('13', 'Itinerary Receipt of E-Ticket'),
            ('14', 'Electronic Railway Ticket'),
            ('15', 'Tax Payment Certificate (Deed Tax)'),
            ('16', 'Uniform Receipt for Central Non-Tax Revenue (Land Transfer Premium)'),
            ('05', 'Fiscal Receipt'),
            ('06', 'Court Ruling'),
            ('09', 'Other Proof of Deduction'),
        ],
        string='Voucher Type'
    )
    voucher_total = fields.Monetary(string='Voucher Total')
    deduct_amount = fields.Monetary(string='Deduct Amount')
    e_fapiao_number = fields.Char(string='E-Fapiao Number')
    receipt_code = fields.Char(string='Receipt Code')
    receipt_number = fields.Char(string='Receipt Number')
    voucher_number = fields.Char(string='Voucher Number')
    issue_date = fields.Date(string='Issue Date')
    remarks = fields.Text(string='Remarks')

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    @api.constrains('voucher_total', 'deduct_amount')
    def _check_amount(self):
        for bdl in self:
            if bdl.deduct_amount > bdl.voucher_total:
                raise ValidationError(self.env._("The deducted amount cannot exceed the voucher total amount."))
