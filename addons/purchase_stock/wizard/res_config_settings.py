from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    module_stock_dropshipping = fields.Boolean(string="Dropshipping")
    days_to_purchase = fields.Float(
        related="company_id.days_to_purchase",
        readonly=False,
    )
    is_installed_sale = fields.Boolean(string="Is the Sale Module Installed")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            is_installed_sale=self.env["ir.module.module"]
            .search([("name", "=", "sale"), ("state", "=", "installed")])
            .id,
        )
        return res
