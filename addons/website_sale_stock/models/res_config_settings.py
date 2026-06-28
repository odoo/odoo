# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    website_warehouse_id = fields.Many2one(
        "stock.warehouse",
        related="website_id.warehouse_id",
        domain="[('company_id', '=', website_company_id)]",
        readonly=False,
    )
