from odoo import fields, models


class CustomerDelayReport(models.Model):
    _name = "customer.delay.report"
    _inherit = ["mixin.order.delay.report"]
    _description = "Customer Delay Report"
    _auto = False

    _order_line_table = "sale_order_line"
    _order_table = "sale_order"
    _link_column = "sale_line_id"
    _date_commitment_alias = "o"
    _partner_location_field = "location_dest_id"
    _partner_location_usage = "customer"

    partner_id = fields.Many2one(string="Customer")
