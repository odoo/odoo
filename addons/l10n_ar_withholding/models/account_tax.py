# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class AccountTax(models.Model):

    _inherit = 'account.tax'

    l10n_ar_withholding = fields.Selection([('supplier', 'Supplier'), ('customer', 'Customer')], 'Argentinean Withholding')
    l10n_ar_withholding_amount_type = fields.Selection([
        ('untaxed_amount', 'Untaxed Amount'),
        ('tax_amount', 'Tax Amount'),
        ('total_amount', 'Total Amount'),
    ], 'Withholding Base Amount', help='Base amount used to get withholding amount',)
    l10n_ar_withholding_sequence_id = fields.Many2one(
        'ir.sequence', 'Withholding Number Sequence', copy=False,
        domain=[('code', '=', 'l10n_ar.account.tax.withholding')],
        context="{'default_code': 'l10n_ar.account.tax.withholding', 'default_name': name}",
        help='If no sequence provided then it will be required for you to enter withholding number when registering one.',)

    def _get_tax_vals(self, company, tax_template_to_tax):
        vals = super()._get_tax_vals(company, tax_template_to_tax)
        vals.update({
            'l10n_ar_withholding': self.l10n_ar_withholding,
            'l10n_ar_withholding_amount_type': self.l10n_ar_withholding_amount_type,
        })
        return vals

    # TODO agregar constrains similares a italia?
    # @api.constrains('amount', 'l10n_it_withholding_type', 'l10n_it_withholding_reason', 'l10n_it_pension_fund_type')
    # def _validate_withholding(self):
    #     for tax in self:
    #         if tax.l10n_it_withholding_type and tax.l10n_it_withholding_type != 'RT04' and tax.amount >= 0:
    #             raise ValidationError(_("Tax '%s' has a withholding type so the amount must be negative.", tax.name))
    #         if tax.l10n_it_withholding_type and not tax.l10n_it_withholding_reason:
    #             raise ValidationError(_("Tax '%s' has a withholding type, so the withholding reason must also be specified", tax.name))
    #         if tax.l10n_it_withholding_reason and not tax.l10n_it_withholding_type:
    #             raise ValidationError(_("Tax '%s' has a withholding reason, so the withholding type must also be specified", tax.name))
    #         if (tax.l10n_it_withholding_type or tax.l10n_it_withholding_reason) and tax.l10n_it_pension_fund_type:
    #             raise ValidationError(_("Tax '%s' cannot be both a Withholding tax and a Pension fund tax. Please create two separate ones.", tax.name))

# TODO keep reusing same rep lines or create newones?
# class AccountTaxRepartitionLine(models.Model):
#     _inherit = "account.tax.repartition.line"

#     account_id = fields.Many2one(string="Account",
#         comodel_name='account.account',
#         domain="[('deprecated', '=', False), ('company_id', '=', company_id), ('internal_type', 'not in', ('receivable', 'payable'))]",
#         check_company=True,
#         help="Account on which to post the tax amount")
#     tag_ids = fields.Many2many(string="Tax Grids", comodel_name='account.account.tag', domain=[('applicability', '=', 'taxes')], copy=True)
#     payment_tax_id = fields.Many2one(comodel_name='account.tax',
#         check_company=True,
#         help="The tax set to apply this distribution on invoices. Mutually exclusive with refund_tax_id")
#     refund_payment_tax_id = fields.Many2one(comodel_name='account.tax',
#         check_company=True,
#         help="The tax set to apply this distribution on invoices. Mutually exclusive with refund_tax_id")
#     company_id = fields.Many2one(string="Company", comodel_name='res.company', compute="_compute_company", store=True, help="The company this distribution line belongs to.")

#     @api.constrains('invoice_tax_id', 'refund_tax_id')
#     def validate_tax_template_link(self):
#         for record in self:
#             if record.invoice_tax_id and record.refund_tax_id:
#                 raise ValidationError(_("Tax distribution lines should apply to either invoices or refunds, not both at the same time. invoice_tax_id and refund_tax_id should not be set together."))

#     @api.depends('invoice_tax_id.company_id', 'refund_tax_id.company_id', 'payment_tax_id.company_id', 'refund_payment_tax_id.company_id')
#     def _compute_company(self):
#         payment_records = self.filtered(lambda x: x.payment_tax_id or x.refund_payment_tax_id)
#         for record in _compute_company:
#             record.company_id = record.payment_tax_id and record.payment_tax_id.company_id.id or record.refund_payment_tax_id.company_id.id
#         return super(AccountTaxRepartitionLine, self - payment_records)._compute_company()

#     @api.depends('invoice_tax_id', 'refund_tax_id')
#     def _compute_tax_id(self):
#         payment_records = self.filtered(lambda x: x.payment_tax_id or x.refund_payment_tax_id)
#         for record in payment_records:
#             record.tax_id = record.payment_tax_id or record.refund_payment_tax_id
#         return super(AccountTaxRepartitionLine, self - payment_records)._compute_tax_id()
