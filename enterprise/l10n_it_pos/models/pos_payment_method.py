from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    it_payment_code = fields.Char(
        string='Payment Code',
        help=(
            "0 = Cash\n"
            "1 = Check\n"
            "2 = Credit or credit card. Credit now interpreted as mixed not paid\n"
            "3 = Ticket\n"
            "4 = Multiple tickets\n"
            "5 = Not paid\n"
            "6 = Payment discount"
        )
    )
    it_payment_index = fields.Integer(string='Payment Index', default=1)

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        return result + ['it_payment_code', 'it_payment_index']
