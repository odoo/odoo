# Copyright 2024 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details).

from odoo import api, fields, models


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    auto_validate_return = fields.Boolean(
        default=True,
        help="If set, return to this operation type will be validated automatically",
    )
