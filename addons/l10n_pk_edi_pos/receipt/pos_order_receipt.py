from odoo import models
from odoo.tools import file_open, formatLang
from odoo.tools.image import image_data_uri


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def _is_item_count_excluded_line(self, line):
        return super()._is_item_count_excluded_line(line) or (
            self.config_id.l10n_pk_edi_pos_enabled and line in self._l10n_pk_edi_pos_fee_lines()
        )

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        if self.company_id.country_id.code != 'PK':
            return data

        if data['order'].get('l10n_pk_edi_pos_qr'):
            data['extra_data']['l10n_pk_edi_pos_qr'] = self._order_receipt_generate_qr_code(data['order']['l10n_pk_edi_pos_qr'])
            # wkhtmltoimage renders the receipt without local file access, so the logo is embedded.
            with file_open('l10n_pk_edi_pos/static/src/img/img_fbr_pos.png', 'rb') as logo:
                data['image']['l10n_pk_edi_pos_fbr_logo'] = image_data_uri(logo.read())
        if self.config_id.l10n_pk_edi_pos_enabled:
            data['conditions']['l10n_pk_edi_pos_enabled'] = True
            self._l10n_pk_edi_pos_add_receipt_data(data)
        return data

    def _l10n_pk_edi_pos_add_receipt_data(self, data):
        # The receipt prints the figures sent to the FBR; lines it does not report get no tax columns.
        item_by_line = dict(zip(self._l10n_pk_edi_pos_reported_lines(), self._l10n_pk_edi_pos_line_details()))
        fee_lines = self._l10n_pk_edi_pos_fee_lines()
        # The FBR gets positive amounts for a refund, which the receipt prints negatively.
        sign = -1 if self.is_refund_or_negative() else 1
        for line_data in data['lines']:
            line = self.lines.browse(line_data['id'])
            item = item_by_line.get(line)
            line_data.update({
                'unit_price': self._order_receipt_format_currency(line._compute_amount_line_all(1)['price_subtotal']),
                'l10n_pk_edi_pos_is_service_fee': line in fee_lines,
                'l10n_pk_edi_pos_tax_rate': f"{item['TaxRate']:g}%" if item else '',
                'l10n_pk_edi_pos_tax_amount': self._l10n_pk_edi_pos_format_amount(sign * item['TaxCharged']) if item else '',
                'l10n_pk_edi_pos_total': self._l10n_pk_edi_pos_format_amount(sign * item['TotalAmount'] if item else line.price_subtotal_incl),
            })

        subtotal = sum(item['TotalAmount'] - item['TaxCharged'] - item['FurtherTax'] for item in item_by_line.values())
        received = sum(payment.amount for payment in self.payment_ids if not payment.is_change)
        data['extra_data']['prices']['subtotal_amount'] = self._order_receipt_format_currency(sign * subtotal)
        data['extra_data'].update({
            'l10n_pk_edi_pos_service_fee': self._order_receipt_format_currency(sum(fee_lines.mapped('price_subtotal_incl'))) if fee_lines else False,
            'l10n_pk_edi_pos_received': self._order_receipt_format_currency(received),
        })

    def _l10n_pk_edi_pos_format_amount(self, amount):
        # The FBR columns print bare amounts; wkhtmltoimage needs plain spaces, as in _order_receipt_format_currency.
        return formatLang(self.env, amount, digits=self.currency_id.decimal_places).replace('\xa0', ' ')
