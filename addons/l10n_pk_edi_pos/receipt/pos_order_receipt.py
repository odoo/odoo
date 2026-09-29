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
        AccountTax = self.env['account.tax']
        base_lines = self.lines._prepare_base_lines_for_taxes_computation()
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        base_line_by_id = {base_line['record'].id: base_line for base_line in base_lines}
        fee_lines = self._l10n_pk_edi_pos_fee_lines()

        # Base lines are positive for a refund, which the receipt prints negatively.
        sign = -1 if self.is_refund_or_negative() else 1
        subtotal = service_fee = 0.0
        for line_data in data['lines']:
            base_line = base_line_by_id[line_data['id']]
            line = base_line['record']
            tax_details = base_line['tax_details']
            taxes_data = tax_details['taxes_data']
            untaxed = tax_details['total_excluded_currency'] + tax_details['delta_total_excluded_currency']
            total = untaxed + sum(tax_data['tax_amount_currency'] for tax_data in taxes_data)
            is_service_fee = line in fee_lines
            if is_service_fee:
                service_fee += total
            else:
                subtotal += untaxed

            # Same rate and sales tax as sent to the FBR, see _l10n_pk_edi_pos_line_details.
            product = line.product_id
            rate_base = tax_details['raw_total_excluded_currency']
            if product.l10n_pk_is_fbr_3rd_schedule:
                rate_base = self._l10n_pk_edi_pos_sale_base(base_line, product.lst_price)
            sales_tax = sum(tax_data['tax_amount_currency'] for tax_data in taxes_data if not tax_data['tax'].l10n_pk_is_further_tax)

            line_data.update({
                'unit_price': self._order_receipt_format_currency(line._compute_amount_line_all(1)['price_subtotal']),
                'l10n_pk_edi_pos_is_service_fee': is_service_fee,
                'l10n_pk_edi_pos_tax_rate': f"{self._l10n_pk_edi_pos_tax_rate(taxes_data, rate_base):g}%",
                'l10n_pk_edi_pos_tax_amount': self._l10n_pk_edi_pos_format_amount(sign * sales_tax),
                'l10n_pk_edi_pos_total': self._l10n_pk_edi_pos_format_amount(sign * total),
            })

        received = sum(payment.amount for payment in self.payment_ids if not payment.is_change)
        data['extra_data']['prices']['subtotal_amount'] = self._order_receipt_format_currency(sign * subtotal)
        data['extra_data'].update({
            'l10n_pk_edi_pos_service_fee': self._order_receipt_format_currency(sign * service_fee) if fee_lines else False,
            'l10n_pk_edi_pos_received': self._order_receipt_format_currency(received),
        })

    def _l10n_pk_edi_pos_format_amount(self, amount):
        # The FBR columns print bare amounts; wkhtmltoimage needs plain spaces, as in _order_receipt_format_currency.
        return formatLang(self.env, amount, digits=self.currency_id.decimal_places).replace('\xa0', ' ')
