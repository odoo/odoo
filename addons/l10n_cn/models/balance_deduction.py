from odoo import api, fields, models
from odoo.exceptions import ValidationError


class L10nCnBalanceDeduction(models.Model):
    _name = 'l10n_cn.balance.deduction'
    _description = 'Balance Deduction Information'
    _check_company_auto = True

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
        string='Voucher Type',
    )
    voucher_total = fields.Monetary(string='Voucher Total')
    deduct_amount = fields.Monetary(string='Deduct Amount')
    e_fapiao_number = fields.Char(string='E-Fapiao Number')
    receipt_code = fields.Char(string='Receipt Code')
    receipt_number = fields.Char(string='Receipt Number')
    voucher_number = fields.Char(string='Voucher Number')
    issue_date = fields.Date(string='Issue Date')
    remarks = fields.Text(string='Remarks')
    expense_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Expense Account",
        check_company=True,
    )

    # Related fields
    company_id = fields.Many2one(
        related='move_line_id.company_id',
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    currency_id = fields.Many2one(related='move_line_id.currency_id')
    accounting_date = fields.Date(
        related='move_line_id.l10n_cn_output_vat_offset_move_id.date',
        string="Accounting Date",
    )
    output_vat_offset_move_id = fields.Many2one(
        related='move_line_id.l10n_cn_output_vat_offset_move_id',
        string="Journal Entry",
        check_company=True,
    )
    invoice_number = fields.Char(
        related='move_line_id.move_id.name',
        string="Invoice Number",
    )
    fapiao_number = fields.Char(
        related='move_line_id.move_id.fapiao',
        string="Fapiao Number",
    )
    invoice_date = fields.Date(
        related='move_line_id.invoice_date',
        string="Invoice Date",
    )
    vat_differential_taxation = fields.Selection(
        related='move_line_id.move_id.l10n_cn_differential_taxation_method',
        string="VAT Differential Taxation",
    )
    product_id = fields.Many2one(
        related='move_line_id.product_id',
        string="Product",
        check_company=True,
    )
    tax_inclusive_amount = fields.Monetary(
        related='move_line_id.price_total',
        string="Tax Inclusive Amount",
    )
    move_type = fields.Selection(
        related='move_line_id.move_id.move_type',
        string="Type",
    )

    @api.constrains('voucher_total', 'deduct_amount')
    def _check_amount(self):
        for bdl in self:
            if bdl.deduct_amount > bdl.voucher_total:
                raise ValidationError(self.env._("The deducted amount cannot exceed the voucher total amount."))
