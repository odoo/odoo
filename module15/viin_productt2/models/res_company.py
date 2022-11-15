
from odoo import  fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    portal_confirmation_sign = fields.Boolean(string='Online Signature', default=True)
    portal_confirmation_pay = fields.Boolean(string='Online Payment')
    note = fields.Text(string='Note:')
    quotation_validity_days = fields.Integer(default=30, string="Default Quotation Validity (Days)")

    

    _sql_constraints = [('check_quotation_validity_days', 'CHECK(quotation_validity_days > 0)', 'Quotation Validity is required and must be greater than 0.')]
