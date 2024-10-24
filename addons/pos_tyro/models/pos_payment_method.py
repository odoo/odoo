# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, release


class PosPaymentMethod(models.Model):
    _inherit = ["pos.payment.method"]

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [("tyro", "Tyro")]

    tyro_mode = fields.Selection([("prod", "Production Mode"), ("test", "Test Mode"), ("simulator", "Simulator Mode")], default="prod")
    tyro_merchant_id = fields.Char("Tyro Merchant ID")
    tyro_terminal_id = fields.Char("Tyro Terminal ID")
    tyro_integration_key = fields.Char("Integration Key")
    tyro_integrated_receipts = fields.Boolean("Integrated Receipts", help="If enabled, the Tyro receipt will be embedded in the Odoo receipt. Otherwise the terminal will print a separate payment receipt.")
    tyro_surcharge_product_id = fields.Many2one("product.product", string="Surcharge Product", default=lambda self: self._get_default_tyro_surcharge_product())

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ["tyro_merchant_id", "tyro_terminal_id", "tyro_integration_key", "tyro_mode", "tyro_integrated_receipts", "tyro_surcharge_product_id"]
        return params

    def action_pair_tyro_terminal(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "pair_tyro_terminal",
            "target": "new",
            "name": "Pair Tyro Terminal",
            "params": {
                "payment_method_id": self.id,
                "tyro_mode": self.tyro_mode,
                "merchant_id": self.tyro_merchant_id,
                "terminal_id": self.tyro_terminal_id,
            }
        }

    def get_tyro_product_info(self):
        return {
            "posProductVendor": "Odoo",
            "posProductName": "Odoo Point of Sale",
            "posProductVersion": release.series,
            "apiKey": "testApiKey",
        }

    def _get_default_tyro_surcharge_product(self):
        surcharge_product_id = self.env.ref("pos_tyro.product_product_tyro_surcharge", raise_if_not_found=False)
        if not surcharge_product_id:
            surcharge_product_id = self.env["product.product"].search([("default_code", "=", "TYRO")], limit=1)
        return surcharge_product_id
