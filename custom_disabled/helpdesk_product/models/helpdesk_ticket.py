from odoo import fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    product_id = fields.Many2one(string="Product", comodel_name="product.product")
