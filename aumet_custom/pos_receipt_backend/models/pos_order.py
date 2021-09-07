# -*- coding: utf-8 -*-
import base64
import psycopg2
import pytz
from datetime import timedelta
from odoo import api, fields, models, tools, _
from odoo.http import request
from io import BytesIO

try:
    import qrcode
except ImportError:
    qrcode = None


class pos_order(models.Model):
    _inherit = "pos.order"

    def get_payment_methods(self):
        payment_method_list = []
        payment_method_list_dummy = []
        for rec in self:
            for line in rec.payment_ids:
                if line.payment_method_id.name not in payment_method_list_dummy:
                    payment_method_list_dummy.append(line.payment_method_id.name)
                    payment_line = {
                        'name': line.payment_method_id.name,
                        'amount': line.amount,
                    }
                    payment_method_list.append(payment_line)
        return payment_method_list

    def get_total_discount(self):
        discount = 0
        for rec in self:
            for line in rec.lines:
                discount += (line.price_unit * (line.discount / 100) * line.qty)
        return discount

    def action_receipt_qrcode(self, name):
        if name:
            qr_code = name
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_code)
            qr.make(fit=True)

            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            qr_code_image = base64.b64encode(temp.getvalue())

            # res.sh_qr_code_img = qr_code_image
            return qr_code_image
