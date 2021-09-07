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


class PosOrder(models.Model):
    _inherit = "pos.order"
    _description = "Point of Sale Orders"

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

class PosConfig(models.Model):
    _inherit = "pos.config"

    allow_qr_code_receipt = fields.Boolean('Allow QR Code Receipt', default=1)
