# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    auto_print_carrier_labels = fields.Boolean(
        "Auto Print Carrier Labels",
        help="Automatically print the carrier labels of the picking when they are created.",
    )
    auto_print_export_documents = fields.Boolean(
        "Auto Print Export Documents",
        help=(
            "Automatically print the export documents of the picking when they are created. "
            "Availability of export documents depends on the carrier and the destination."
        ),
    )
