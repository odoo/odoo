from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # Added field
    woo_backend_id = fields.Many2one("woo.backend", string="WooCommerce Backend")
