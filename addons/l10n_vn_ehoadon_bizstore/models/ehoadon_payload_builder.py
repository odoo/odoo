# -*- coding: utf-8 -*-
"""Build eHoaDon AddOrUpdateEInvoiceDto from account.move."""
from odoo import fields


# .NET swagger lists string names but type=int — use int ordinals.
STATUS_NEW = 0
CURRENCY_VND = 0
DISCOUNT_NONE = 0

# Multi-rate (VatPerItem) serials: header vatRate must be 0, lines carry their own rate.
HEADER_VAT_RATE_DEFAULT = 0

# InvoiceType enum order (swagger InvoiceType)
INVOICE_TYPE_NORMAL = 0
INVOICE_TYPE_REPLACE = 1
INVOICE_TYPE_ADJUSTED_UP = 2
INVOICE_TYPE_ADJUSTED_DOWN = 3
INVOICE_TYPE_ADJUSTED_INFO = 4

# ExplanationType / InformType for SendErrrorInform
EXPLANATION_BY_TAXPAYER = 0
INFORM_TYPE_ADJUSTED = 2  # InformType: New, Report, Adjusted, Replace, …

BUSINESS_TYPE_MAP = {
    'replace': INVOICE_TYPE_REPLACE,
    'adjusted_up': INVOICE_TYPE_ADJUSTED_UP,
    'adjusted_down': INVOICE_TYPE_ADJUSTED_DOWN,
    'adjusted_info': INVOICE_TYPE_ADJUSTED_INFO,
}


class EhoadonPayloadBuilder:
    def __init__(self, invoice):
        self.invoice = invoice

    def build(self, status=STATUS_NEW, include_remote_ids=False):
        self.invoice.ehoadon_issue_date = fields.Datetime.now()
        template = self.invoice._ehoadon_resolve_template()
        items = self._build_items(template)
        vat_rate = self._header_vat_rate(template)
        payload = {
            'serial': template.serial,
            'arisingDate': self.invoice._ehoadon_format_date(self.invoice.ehoadon_issue_date),
            'vatRate': vat_rate,
            'status': status,
            'paymentMethod': int(template.payment_method or '3'),
            'currencyType': CURRENCY_VND,
            'exchangeRate': 0,
            'eInvoiceItems': items,
            'invoiceCustomer': self.invoice._ehoadon_build_invoice_customer(),
            'note': (self.invoice.narration or '')[:500] if self.invoice.narration else '',
            'isUseCheckDiscount': False,
            'rateCheckDiscount': 0,
            'discountType': DISCOUNT_NONE,
            'checkDuplicate': True,
        }
        if include_remote_ids:
            if self.invoice.ehoadon_invoice_id:
                payload['id'] = self.invoice.ehoadon_invoice_id
            if self.invoice.ehoadon_guid:
                payload['guid'] = self.invoice.ehoadon_guid
            if self.invoice.ehoadon_lookup_code:
                payload['lookupCode'] = self.invoice.ehoadon_lookup_code
            # Draft placeholder 00000000 is rejected by CashRegister (expects an 11-digit MTT code).
            if (self.invoice.ehoadon_invoice_number or '').strip('0'):
                payload['invoiceNumber'] = self.invoice.ehoadon_invoice_number
        return payload

    def build_business(self, invoice_type, original_invoice_id, status=STATUS_NEW):
        """Wrap AddOrUpdate payload for InvoiceBusiness (adjust/replace).

        eHoaDon prints the "thay thế / điều chỉnh cho hóa đơn số …" line itself.
        """
        return {
            'originalInvoiceId': original_invoice_id,
            'invoiceType': int(invoice_type),
            'invoice': self.build(status=status),
        }

    def build_error_inform(self, *, description, inform_type=INFORM_TYPE_ADJUSTED):
        """Body for SendErrrorInform (API typo kept)."""
        inv = self.invoice
        return {
            'location': (inv.company_id.city or inv.company_id.name or '')[:200],
            'reportDate': inv._ehoadon_format_date(fields.Datetime.now()),
            'explanationType': EXPLANATION_BY_TAXPAYER,
            'isCashRegister': bool(
                inv.ehoadon_template_id and inv.ehoadon_template_id.is_cash_register
            ),
            'sendToTaxAuthorite': True,
            'invoices': [{
                'invoiceId': inv.ehoadon_invoice_id,
                'type': int(inform_type),
                'eInvoiceApplicable': 1,
                'description': (description or '')[:500],
            }],
        }

    def _is_product_line(self, line):
        return (not getattr(line, 'display_type', False)) or getattr(line, 'display_type', False) == 'product'

    def _line_vat_rate(self, line):
        tax_percentage = -2  # Không kê khai (eHoaDon / docs)
        if line.tax_ids:
            percent_taxes = line.tax_ids.filtered(lambda t: t.amount_type == 'percent')
            if percent_taxes:
                tax_percentage = percent_taxes[0].amount
        return tax_percentage

    def _build_items(self, template):
        sign = 1 if self.invoice.move_type == 'out_invoice' else -1
        is_vat_included = bool(template and template.invoice_mtt)
        single_rate = self._single_rate(template)
        items = []
        order = 0
        for line in self.invoice.invoice_line_ids.filtered(self._is_product_line):
            order += 1
            currency = line.currency_id or self.invoice.currency_id
            qty = line.quantity or 0.0
            vat_rate = self._line_vat_rate(line)

            if is_vat_included:
                unit_price = currency.round(line.price_total / qty) if qty else 0.0
                amount = currency.round(line.price_total)
                vat_amount = 0.0
                total = amount
                send_vat_rate = 0
            elif single_rate is not None:
                # Keep what the customer pays; re-split it at the serial's only rate.
                total = currency.round(line.price_total)
                amount = currency.round(total / self._rate_factor(single_rate))
                vat_amount = total - amount
                unit_price = currency.round(amount / qty) if qty else 0.0
                send_vat_rate = single_rate
            else:
                unit_price = currency.round(line.price_subtotal / qty) if qty else 0.0
                amount = currency.round(line.price_subtotal)
                vat_amount = currency.round(line.price_total - line.price_subtotal)
                total = currency.round(line.price_total)
                send_vat_rate = vat_rate

            items.append({
                'productName': line.product_id.name or line.name or '',
                'productNumber': line.product_id.default_code or '',
                'unit': line.product_uom_id.name if line.product_uom_id else '',
                'quantity': qty * sign,
                'price': unit_price,
                'vatRate': send_vat_rate,
                'amount': amount * sign,
                'vatAmount': vat_amount * sign,
                'totalAmount': total * sign,
                'displayOrder': order,
                'free': False,
                'discount': False,
                'discountRate': 0,
                'discountAmount': 0,
                # Without these eHoaDon recomputes quantity * rounded price and drifts from Odoo.
                'addAmount': amount * sign,
                'addVatAmount': vat_amount * sign,
                'currencyType': CURRENCY_VND,
            })
        if single_rate is not None and items:
            self._balance_single_rate(items, single_rate, self.invoice.currency_id)
        return items

    def _single_rate(self, template):
        """VatPerInvoice serial: eHoaDon applies the header rate to every line, so lines must use it too."""
        if template and not template.invoice_mtt and template.vat_rate_mode == 'per_invoice':
            return template.default_vat_rate
        return None

    def _rate_factor(self, vat_rate):
        # Negative codes (-1 không thuế, -2 không kê khai, -3 khác) carry no tax.
        return 1 + max(vat_rate or 0.0, 0.0) / 100.0

    def _balance_single_rate(self, items, vat_rate, currency):
        """eHoaDon recomputes tax as sum(amount) * rate: push per-line rounding into the last line."""
        total = sum(item['totalAmount'] for item in items)
        target = currency.round(total / self._rate_factor(vat_rate))
        diff = target - sum(item['amount'] for item in items)
        if not diff:
            return
        last = items[-1]
        for key in ('amount', 'addAmount'):
            last[key] += diff
        for key in ('vatAmount', 'addVatAmount'):
            last[key] -= diff
        if last['quantity']:
            last['price'] = currency.round(last['amount'] / last['quantity'])

    def _header_vat_rate(self, template):
        # VAT-inclusive lines carry vatRate 0; a header rate would make eHoaDon add tax on top.
        if template and template.invoice_mtt:
            return HEADER_VAT_RATE_DEFAULT
        if template and template.vat_rate_mode == 'per_invoice':
            return template.default_vat_rate
        return HEADER_VAT_RATE_DEFAULT
