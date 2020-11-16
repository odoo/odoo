# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api
from odoo.addons.account.models.account_tax import TYPE_TAX_USE


class AccountTax(models.Model):

    _inherit = 'account.tax'

    TYPE_TAX_USE += [('customer', 'Customer Payment'), ('supplier', 'Supplier Payment')]
    withholding_amount_type = fields.Selection([
        ('untaxed_amount', 'Untaxed Amount'),
        ('tax_amount', 'Tax Amount'),
        ('total_amount', 'Total Amount'),
    ],
        'Base Amount',
        help='Base amount used to get withholding amount',
    )

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
