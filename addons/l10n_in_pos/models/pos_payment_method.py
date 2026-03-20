# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.image import image_data_uri
from odoo.tools.urls import urljoin as url_join


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    upi_identifier = fields.Char(string='UPI ID', help="UPI ID to be used for UPI QR payments.")
    qr_payment_icon_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string='QR Payment Icons',
        help="Icons that will be displayed in the QR dialog to indicate the available payment options.",
        bypass_search_access=True
    )

    _check_unique_upi_identifier = models.Constraint(
        'unique(upi_identifier)',
        "Payment Method with this UPI ID already exist.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        if self.env.company.country_code == 'IN':
            fields += ['upi_identifier']
        return fields

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        for record in read_records:
            if record['payment_method_type'] == 'qr_code':
                payment_method = self.browse(record['id'])
                record['_qr_payment_icon_urls'] = [[icon.id, url_join(config.get_base_url(), icon.local_url)] for icon in payment_method.qr_payment_icon_ids]
        return read_records

    def get_qr_code(self, amount, free_communication, structured_communication, currency, debtor_partner):
        self.ensure_one()
        if self.payment_method_type == 'qr_code' and self.qr_code_method == 'upi':
            if not self.upi_identifier:
                raise UserError(_("Please set a UPI ID for the payment method '%s'.", self.name))
            payment_url = f"upi://pay?pa={self.upi_identifier}&am={amount}&cu={self.journal_id.currency_id.name or self.env.company.currency_id.name}"
            barcode = self.env['ir.actions.report'].barcode(barcode_type='QR', value=payment_url, width=120, height=120, barBorder=0)
            return image_data_uri(base64.b64encode(barcode))
        return super().get_qr_code(amount, free_communication, structured_communication, currency, debtor_partner)
