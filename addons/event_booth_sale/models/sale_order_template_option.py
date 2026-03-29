from odoo import fields, models

class SaleOrderTemplateOption(models.Model):
    _inherit = "sale.order.template.option"

    product_id = fields.Many2one(domain="[('sale_ok', '=', True), ('detailed_type', 'not in', ['event', 'event_booth'])]")
