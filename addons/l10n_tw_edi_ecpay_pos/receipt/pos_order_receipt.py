# Part of Odoo. See LICENSE file for full copyright and licensing details.
from urllib.parse import quote
from zoneinfo import ZoneInfo

from odoo import api, models

from odoo.tools.date_utils import localized


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    @api.model
    def get_receipt_template_for_pos_frontend(self):
        names = [
            'l10n_tw_edi_ecpay_pos.ecpay_certificate_receipt',
            'l10n_tw_edi_ecpay_pos.ecpay_transaction_receipt',
        ]
        return super().get_receipt_template_for_pos_frontend() + [
            [name, self.env['ir.qweb']._get_template(name)[1]] for name in names
        ]

    def _order_receipt_generate_line_data(self):
        lines = super()._order_receipt_generate_line_data()
        for line, data in zip(self.lines, lines):
            # Add custom code here to always get the price including tax for the receipt
            data['price_subtotal_incl_custom'] = self._order_receipt_format_currency(line.price_subtotal_incl)
            data['price_unit_incl_custom'] = self._order_receipt_format_currency(line.price_subtotal_incl / data['qty'] if line.qty else 0)
        return lines

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        not_print_ecpay_invoice = any((
            self.company_id.account_fiscal_country_id.code != 'TW',
            not self.config_id.is_ecpay_enabled,
            not self.l10n_tw_edi_is_print,
            self.l10n_tw_edi_is_b2b,
            self.ecpay_error,
        ))
        if not_print_ecpay_invoice:
            return data

        data['extra_data']['isPrintEcpayInvoice'] = not not_print_ecpay_invoice
        data['extra_data']['ecpay_error'] = self.ecpay_error
        data['extra_data']['account_fiscal_country_code'] = self.company_id.account_fiscal_country_id.code
        data['extra_data']['invoice_month'] = self.invoice_month
        data['extra_data']['iis_number'] = self.iis_number
        data['extra_data']['iis_create_date'] = (
            localized(self.iis_create_date)
            .astimezone(ZoneInfo("Asia/Taipei"))
            .strftime("%Y-%m-%d %H:%M:%S")
            if self.iis_create_date
            else False
        )
        data['extra_data']['iis_random_number'] = self.iis_random_number
        data['extra_data']['l10n_tw_edi_invoice_amount'] = self._order_receipt_format_currency(self.l10n_tw_edi_invoice_amount)
        data['extra_data']['iis_tax_amount'] = self._order_receipt_format_currency(self.iis_tax_amount)
        data['extra_data']['total_amount'] = self._order_receipt_format_currency(self.l10n_tw_edi_invoice_amount - self.iis_tax_amount)
        data['extra_data']['l10n_tw_edi_carrier_number'] = self.l10n_tw_edi_carrier_number
        data['extra_data']['l10n_tw_edi_carrier_type'] = self.l10n_tw_edi_carrier_type
        data['extra_data']['l10n_tw_edi_ecpay_seller_identifier'] = self.l10n_tw_edi_ecpay_seller_identifier
        data['image']['pos_barcode'] = self.pos_barcode
        if self.pos_barcode:
            base_url = self.env.company.get_base_url()
            data['image']['pos_barcode_src'] = f"{base_url}/report/barcode/Code128/{quote(self.pos_barcode)}"
        if self.qrcode_left:
            qrcode_left_data = 'data:image/png;base64,' + self.qrcode_left
            data['image']['qrcode_left'] = qrcode_left_data
        if self.qrcode_right:
            qrcode_right_data = 'data:image/png;base64,' + self.qrcode_right
            data['image']['qrcode_right'] = qrcode_right_data
        return data

    def order_receipt_generate_html(self, basic_receipt=False):
        content = super().order_receipt_generate_html(basic_receipt)
        if any((
            self.company_id.account_fiscal_country_id.code != 'TW',
            not self.config_id.is_ecpay_enabled,
            not self.l10n_tw_edi_is_print,
            self.l10n_tw_edi_is_b2b,
            self.ecpay_error,
        )):
            return content

        ecpay_certificate_receipt = self.env['ir.qweb']._render(
            'l10n_tw_edi_ecpay_pos.ecpay_certificate_receipt',
            values=self.order_receipt_generate_data(basic_receipt),
        )
        ecpay_transaction_receipt = self.env['ir.qweb']._render(
            'l10n_tw_edi_ecpay_pos.ecpay_transaction_receipt',
            values=self.order_receipt_generate_data(basic_receipt),
        )
        separator = '<div style="display:block; clear:both; height:4mm;"></div>'
        return separator.join([content, ecpay_certificate_receipt, ecpay_transaction_receipt])
