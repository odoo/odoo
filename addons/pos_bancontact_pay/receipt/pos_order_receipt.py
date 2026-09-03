# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.tools import file_open
from odoo.tools.image import image_data_uri


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        if self.payment_ids.filtered(lambda p: p.payment_method_id.payment_provider == "bancontact_pay"):
            data['extra_data']['processed_by_bancontact'] = True
            with file_open('pos_bancontact_pay/static/img/receipt/logo.png', 'rb') as logo_file:
                data['image']['bancontact_logo'] = image_data_uri(logo_file.read())
        return data
