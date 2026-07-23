# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    website_warehouse_id = fields.Many2one(
        "stock.warehouse",
        related="website_id.warehouse_id",
        domain=lambda self: [('company_id', 'in', self.env.companies.ids + self.website_company_id.ids)],
        readonly=False,
    )
