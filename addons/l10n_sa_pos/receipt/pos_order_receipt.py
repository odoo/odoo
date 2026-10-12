# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from zoneinfo import ZoneInfo
from odoo import models, api


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)

        if self.company_id.country_id.code == 'SA':
            data['image']['sa_qr_code'] = self._order_receipt_generate_qr_code(self.compute_sa_qr_code())
            data['conditions']['code_sa'] = True

        return data

    def compute_sa_qr_code(self):
        """
        Generate the QR code for Saudi e-invoicing (ZATCA).
        Equivalent to the JavaScript computeSAQRCode function.
        """
        # Convert datetime to Saudi timezone and format
        ksa_time = self.date_order.astimezone(ZoneInfo("Asia/Riyadh"))
        ksa_timestamp = ksa_time.strftime("%m/%d/%Y, %H:%M:%S")

        # Encode fields
        seller_name_enc = self._compute_qr_code_field(1, self.company_id.name)
        company_vat_enc = self._compute_qr_code_field(2, self.company_id.vat or '')
        timestamp_enc = self._compute_qr_code_field(3, ksa_timestamp)
        invoice_total_enc = self._compute_qr_code_field(4, str(self.amount_total))
        total_vat_enc = self._compute_qr_code_field(5, str(self.amount_tax))

        # Concatenate all encoded arrays
        str_to_encode = (
            seller_name_enc
            + company_vat_enc
            + timestamp_enc
            + invoice_total_enc
            + total_vat_enc
        )

        # Convert to bytes and base64 encode
        binary = bytes(str_to_encode)
        return base64.b64encode(binary).decode('utf-8')

    @api.model
    def _compute_qr_code_field(self, tag, field):
        field_bytes = list(field.encode('utf-8'))
        tag_encoding = [tag]
        length_encoding = [len(field_bytes)]
        return tag_encoding + length_encoding + field_bytes
