# Copyright 2023 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    return_location_id = fields.Many2one(
        "stock.location",
        string="Returns Location",
        config_parameter="sod_crm_claim.return_location_id",
    )
