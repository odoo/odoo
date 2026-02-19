from odoo import fields, models


class WooSaleStatus(models.Model):
    _name = "woo.sale.status"
    _description = "WooCommerce Sale Order Status"

    name = fields.Char(string="Sale Status", required=True)
    code = fields.Char(string="Status Code", required=True)
    is_final_status = fields.Boolean(string="Final Status")
