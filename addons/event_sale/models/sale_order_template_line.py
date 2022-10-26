from odoo import fields, models

class SaleOrderTemplateLine(models.Model):
    _inherit = "sale.order.template.line"

    product_id = fields.Many2one(domain="[('sale_ok', '=', True), ('detailed_type', '!=', 'event'), ('company_id', 'in', [company_id, False])]")
