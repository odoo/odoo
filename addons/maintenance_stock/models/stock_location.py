from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    maintenance_location = fields.Boolean(
        help="Equipment sent here is out for maintenance."
    )
