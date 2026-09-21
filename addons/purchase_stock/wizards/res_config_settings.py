from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    module_stock_dropshipping = fields.Boolean(string="Dropshipping")
    days_to_purchase = fields.Float(
        related="company_id.purchase_config_id.days_to_purchase",
        readonly=False,
    )
    is_installed_sale = fields.Boolean(string="Is the Sale Module Installed")

    @api.model
    def get_values(self):
        res = super().get_values()
        res.update(
            is_installed_sale=bool(
                self.env["ir.module.module"].search_count(
                    [("name", "=", "sale"), ("state", "=", "installed")],
                    limit=1,
                ),
            ),
        )
        return res
