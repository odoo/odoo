from odoo import fields, models


class VendorDelayReport(models.Model):
    _name = "vendor.delay.report"
    _inherit = ["mixin.order.delay.report"]
    _description = "Vendor Delay Report"
    _auto = False

    _order_line_table = "purchase_order_line"
    _order_table = "purchase_order"
    _link_column = "purchase_line_id"
    _date_commitment_alias = "ol"
    _partner_location_field = "location_id"
    _partner_location_usage = "supplier"

    partner_id = fields.Many2one(string="Vendor")
