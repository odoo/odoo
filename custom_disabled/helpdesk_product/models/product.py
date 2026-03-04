from odoo import fields, models


class Product(models.Model):
    _inherit = "product.template"

    ticket_active = fields.Boolean(
        "Available for Helpdesk Tickets", default=True, required=True
    )
