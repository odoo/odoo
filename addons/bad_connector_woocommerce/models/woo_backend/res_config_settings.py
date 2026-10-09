from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Added field to set default backend for woo base
    woo_backend_id = fields.Many2one(
        comodel_name="woo.backend",
        string="Default WooCommerce Backend",
        related="company_id.woo_backend_id",
        readonly=False,
    )
