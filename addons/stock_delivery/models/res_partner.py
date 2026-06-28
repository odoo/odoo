# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    pickup_location_data = fields.Json(
        "Pickup Location Data",
        help="Technical field: information needed by delivery providers in case of pickup point addresses.",
    )
