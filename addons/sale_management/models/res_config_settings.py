# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_sale_order_template = fields.Boolean(
        string="Quotation Templates", implied_group="sale_management.group_sale_order_template"
    )
