from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    glory_websocket_address = fields.Char(string="Cash Machine IP")
    glory_username = fields.Char(string="Cash Machine Username")
    glory_password = fields.Char(string="Cash Machine Password")

    def _selection_payment_method_types(self):
        return super()._selection_payment_method_types() + [
            ("glory_cash", "Cash Machine (Glory)")
        ]

    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + [
            "glory_websocket_address",
            "glory_username",
            "glory_password",
        ]
