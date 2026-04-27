# coding: utf-8
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_co_edi_brand = fields.Char(string='Brand', help='Reported brand in the Colombian electronic invoice.')
    l10n_co_edi_customs_code = fields.Char(string='Customs Code', help='10 digits Custome Code used on Exportation invoices.')
    l10n_co_edi_ref_nominal_tax = fields.Float(string='Specific Component Nominal Taxes', help='For IBUA tax: Volume in milliliters.\nFor ICL tax: % of alcohol of the beverage.')
