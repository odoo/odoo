import json
import logging
from urllib.parse import urlencode

import requests

from odoo import api, fields, models
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import UserError
from odoo.tools import BinaryBytes, float_round

_logger = logging.getLogger(__name__)

POS_SUBMIT_PATH = '/api/l10n_pk_edi_pos/1/post'
DONE_STATES = ('successful', 'successful_demo')


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_pk_edi_pos_enabled = fields.Boolean(related='config_id.l10n_pk_edi_pos_enabled')
    l10n_pk_edi_pos_invoice_number = fields.Char(
        string="FBR Invoice Number",
        copy=False,
        readonly=True,
        help="Invoice number returned by the FBR after submitting this order.",
    )
    l10n_pk_edi_pos_qr = fields.Char(
        string="FBR QR",
        copy=False,
        readonly=True,
        help="QR code content returned by the FBR after submitting this order.",
    )
    l10n_pk_edi_pos_error = fields.Text(
        string="FBR Error",
        copy=False,
        readonly=True,
        help="Error returned by the FBR when the order submission failed.",
    )
    l10n_pk_edi_pos_state = fields.Selection(
        selection=[
            ('to_send', "To Send"),
            ('successful', "Successful"),
            ('unsuccessful', "Unsuccessful"),
            ('successful_demo', "Successful (Demo)"),
        ],
        string="FBR State",
        default='to_send',
        copy=False,
        readonly=True,
        help="State of the order submission to the FBR.",
    )
    l10n_pk_edi_pos_payload = fields.Binary(
        string="FBR Payload",
        compute='_compute_l10n_pk_edi_pos_payload',
        help="JSON payload submitted to the FBR, downloadable while the submission fails.",
    )

    @api.depends('country_code', 'l10n_pk_edi_pos_error')
    def _compute_l10n_pk_edi_pos_payload(self):
        for order in self:
            if order.country_code == 'PK' and order.l10n_pk_edi_pos_error:
                payload = order._l10n_pk_edi_pos_generate_json()
                order.l10n_pk_edi_pos_payload = BinaryBytes(json.dumps(payload, indent=4, default=str).encode())
            else:
                order.l10n_pk_edi_pos_payload = False

    def download_l10n_pk_edi_pos_payload(self):
        params = urlencode({
            'model': self._name,
            'id': self.id,
            'field': 'l10n_pk_edi_pos_payload',
            'filename': f"FBR Request {self._l10n_pk_edi_pos_usin()}.json",
            'mimetype': 'application/json',
            'download': 'true',
        })
        return {'type': 'ir.actions.act_url', 'url': '/web/content/?' + params, 'target': 'new'}

    def _l10n_pk_edi_pos_connect_to_server(self, mode, auth_token, payload, url_path, timeout=30):
        """POST to the Pakistan POS IAP proxy, which forwards to the FBR from a static IP."""
        # The proxy reads the invoice from the request body, so its own parameters travel in the query
        # string — except the FBR token, kept in a header so it stays out of the proxy access logs.
        query = {
            'mode': mode,
            'dbuuid': self.env['ir.config_parameter'].sudo().get_str('database.uuid'),
        }
        endpoint = iap_tools.iap_get_endpoint(self.env)
        try:
            # The proxy answers with an HTTP status code, so a rejection still carries a JSON body.
            return requests.post(
                endpoint + url_path,
                params=query,
                data=json.dumps(payload, default=str),
                headers={'Content-Type': 'application/json', 'X-FBR-Token': auth_token},
                timeout=timeout,
            ).json()
        except (requests.exceptions.RequestException, ValueError) as error:
            _logger.warning("FBR POS submission transport error: %s", error)
            return {'error': {'code': 'CONNECTION_ERROR', 'message': str(error)}}

    def _l10n_pk_edi_pos_parse_response(self, response):
        """Return None on success, else a human-readable error message."""
        if error := response.get('error'):
            if isinstance(error, dict):
                error = error.get('message')
            return error or self.env._("Unexpected error while contacting the FBR.")
        # The FBR returns Code either as an int or a string.
        if str(response.get('Code')) != '100' or response.get('Errors'):
            return response.get('Errors') or response.get('Response') or self.env._("FBR rejected the invoice.")
        if not response.get('InvoiceNumber'):
            return self.env._("FBR did not return an invoice number.")
        return None

    def _l10n_pk_edi_pos_fee_lines(self):
        self.ensure_one()
        fee_product = self.config_id.l10n_pk_edi_pos_service_fee_product_id
        if not fee_product:
            return self.env['pos.order.line']
        return self.lines.filtered(lambda ln: ln.product_id == fee_product)

    def _l10n_pk_edi_pos_reported_lines(self):
        self.ensure_one()
        lines = self.lines - self._l10n_pk_edi_pos_fee_lines()
        return lines.filtered(lambda ln: ln.product_id and ln.qty)

    def _l10n_pk_edi_pos_untaxed_lines(self):
        self.ensure_one()
        # Further tax is no substitute for a sales tax, so a line taxed only by it
        # is still untaxed.
        return self._l10n_pk_edi_pos_reported_lines().filtered(lambda ln: all(tax.l10n_pk_is_further_tax for tax in ln.tax_ids))

    def _l10n_pk_edi_pos_wrong_way_lines(self):
        self.ensure_one()
        sign = -1 if self.is_refund_or_negative() else 1
        return self._l10n_pk_edi_pos_reported_lines().filtered(lambda ln: sign * ln.qty < 0)

    def _l10n_pk_edi_pos_check_lines(self):
        """Stop the sale on what only the cart can fix, so the cashier is not left with an
        order that can never be reported."""
        self.ensure_one()
        errors = []
        if untaxed_lines := self._l10n_pk_edi_pos_untaxed_lines():
            errors.append(self.env._(
                "These products have no sales tax, so they cannot be sold: %s.",
                ", ".join(untaxed_lines.product_id.mapped('display_name')),
            ))
        if wrong_way := self._l10n_pk_edi_pos_wrong_way_lines():
            errors.append(self.env._(
                "These lines go against the order and cannot be reported: %s.",
                ", ".join(wrong_way.product_id.mapped('display_name')),
            ))
        if errors:
            raise UserError("\n".join(errors))

    def _l10n_pk_edi_pos_check_data(self):
        """Return every reason this order cannot be submitted, gathered in one pass so
        the cashier does not get a new rejection at each resend."""
        self.ensure_one()
        errors = []
        posid, auth_token = self.config_id._l10n_pk_edi_pos_credentials()
        if not posid:
            errors.append(self.env._("The FBR Shop ID is not configured on this Point of Sale."))
        if not auth_token:
            errors.append(self.env._("The FBR Shop Token is not configured on this Point of Sale."))
        methods = self.payment_ids.payment_method_id
        if not methods:
            errors.append(self.env._("The order has no payment, so its payment mode is unknown."))
        if unmapped := methods.filtered(lambda method: not method.l10n_pk_edi_pos_fbr_payment_code):
            errors.append(self.env._("These payment methods have no FBR Payment Code: %s.", ", ".join(unmapped.mapped('name'))))
        lines = self._l10n_pk_edi_pos_reported_lines()
        # A negative price is how a global discount is booked.
        if negative_price := lines.filtered(lambda ln: ln.price_unit < 0):
            errors.append(self.env._(
                "The FBR does not accept global discounts. Remove these lines: %s.",
                ", ".join(negative_price.product_id.mapped('display_name')),
            ))
        products = lines.product_id
        if without_hs_code := products.filtered(lambda product: not product.hs_code):
            errors.append(self.env._("These products have no HS Code: %s.", ", ".join(without_hs_code.mapped('display_name'))))
        if without_reference := products.filtered(lambda product: not product.default_code):
            errors.append(self.env._("These products have no Internal Reference: %s.", ", ".join(without_reference.mapped('display_name'))))
        return errors

    def _l10n_pk_edi_pos_usin(self):
        self.ensure_one()
        return (self.pos_reference or self.name).replace(" ", "")

    def _l10n_pk_edi_pos_payment_mode(self):
        self.ensure_one()
        codes = set(self.payment_ids.payment_method_id.mapped('l10n_pk_edi_pos_fbr_payment_code'))
        # An order paid with several distinct methods has no single code to report; 5 is Mixed.
        return int(next(iter(codes))) if len(codes) == 1 else 5

    def _l10n_pk_edi_pos_tax_rate(self, taxes_data, base):
        rate = 0
        for tax_data in taxes_data:
            tax = tax_data['tax']
            # Further tax is reported on its own, so it stays out of the rate.
            if tax.l10n_pk_is_further_tax:
                continue
            if tax.amount_type == 'percent':
                rate += tax.amount
            elif base:
                rate += tax_data['raw_tax_amount_currency'] / base * 100
        # The FBR expects the rate as a percentage with at most two decimals.
        return float_round(rate, precision_digits=2)

    def _l10n_pk_edi_pos_sale_base(self, base_line, price_unit):
        self.ensure_one()
        sale_line = {**base_line, 'price_unit': price_unit, 'discount': 0}
        self.env['account.tax']._add_tax_details_in_base_line(sale_line, self.company_id)
        return sale_line['tax_details']['raw_total_excluded_currency']

    def _l10n_pk_edi_pos_line_details(self):
        self.ensure_one()
        currency = self.currency_id
        is_refund = self.is_refund_or_negative()
        lines = self._l10n_pk_edi_pos_reported_lines()
        base_lines = lines._prepare_base_lines_for_taxes_computation()
        AccountTax = self.env['account.tax']
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)

        items = []
        for base_line in base_lines:
            line = base_line['record']
            product = line.product_id
            tax_details = base_line['tax_details']
            taxes_data = tax_details['taxes_data']
            further_tax = currency.round(sum(tax_data['tax_amount_currency'] for tax_data in taxes_data if tax_data['tax'].l10n_pk_is_further_tax))
            tax_charged = currency.round(sum(tax_data['tax_amount_currency'] for tax_data in taxes_data if not tax_data['tax'].l10n_pk_is_further_tax))
            untaxed = currency.round(tax_details['total_excluded_currency'] + tax_details['delta_total_excluded_currency'])
            third = product.l10n_pk_is_fbr_3rd_schedule
            sale_base = self._l10n_pk_edi_pos_sale_base(base_line, product.lst_price if third else base_line['price_unit'])
            rate_base = sale_base if third else tax_details['raw_total_excluded_currency']
            tax_rate = self._l10n_pk_edi_pos_tax_rate(taxes_data, rate_base)
            sale_value = currency.round(sale_base)
            if is_refund:
                item_type = 12 if third else 3
            else:
                item_type = 11 if third else 1
            ref_usin = None
            if is_refund and line.refunded_orderline_id:
                ref_usin = line.refunded_orderline_id.order_id._l10n_pk_edi_pos_usin()
            items.append({
                'ItemCode': product.default_code,
                'ItemName': (line.full_product_name or product.display_name)[:150],
                'Quantity': base_line['quantity'],
                'PCTCode': (product.hs_code or "").replace(".", "")[:8],
                'TaxRate': tax_rate,
                'SaleValue': sale_value,
                'Discount': currency.round(sale_value - untaxed),
                'FurtherTax': further_tax,
                'TaxCharged': tax_charged,
                'TotalAmount': currency.round(untaxed + tax_charged + further_tax),
                'InvoiceType': item_type,
                'RefUSIN': ref_usin,
            })
        return items

    def _l10n_pk_edi_pos_generate_json(self):
        self.ensure_one()
        currency = self.currency_id
        posid = self.config_id._l10n_pk_edi_pos_credentials()[0]
        items = self._l10n_pk_edi_pos_line_details()
        fee_amount = currency.round(sum(self._l10n_pk_edi_pos_fee_lines().mapped('price_subtotal_incl')))
        is_refund = self.is_refund_or_negative()
        partner = self.partner_id
        ref_usin = None
        if is_refund and self.refunded_order_id:
            ref_usin = self.refunded_order_id._l10n_pk_edi_pos_usin()
        return {
            'InvoiceNumber': "",
            'POSID': int(posid) if posid else 0,
            'USIN': self._l10n_pk_edi_pos_usin(),
            'RefUSIN': ref_usin,
            'DateTime': fields.Datetime.to_string(self.date_order),
            'BuyerName': partner.name or "",
            'BuyerNTN': partner.vat or "",
            'BuyerCNIC': (partner.additional_identifiers or {}).get('PK_CN') or "",
            'BuyerPhoneNumber': partner.phone or "",
            'TotalBillAmount': currency.round(sum(item['TotalAmount'] for item in items) + fee_amount),
            'TotalQuantity': sum(item['Quantity'] for item in items),
            'TotalSaleValue': currency.round(sum(item['SaleValue'] for item in items) + fee_amount),
            'TotalTaxCharged': currency.round(sum(item['TaxCharged'] for item in items)),
            'Discount': currency.round(sum(item['Discount'] for item in items)),
            'FurtherTax': currency.round(sum(item['FurtherTax'] for item in items)),
            'PaymentMode': self._l10n_pk_edi_pos_payment_mode(),
            'InvoiceType': 3 if is_refund else 1,
            'Items': items,
        }

    def _l10n_pk_edi_pos_send(self):
        self.ensure_one()
        config = self.config_id
        if not config.l10n_pk_edi_pos_enabled or self.country_code != 'PK':
            return
        self._l10n_pk_edi_pos_check_lines()
        if errors := self._l10n_pk_edi_pos_check_data():
            self._l10n_pk_edi_pos_mark_failed("\n".join(errors))
            return
        mode = 'test' if config.l10n_pk_edi_pos_sandbox else 'prod'
        try:
            auth_token = config._l10n_pk_edi_pos_credentials()[1]
            payload = self._l10n_pk_edi_pos_generate_json()
            response = self._l10n_pk_edi_pos_connect_to_server(mode, auth_token, payload, POS_SUBMIT_PATH)
            error_message = self._l10n_pk_edi_pos_parse_response(response)
        except Exception as error:
            _logger.exception("FBR POS submission failed for order %s", self.name)
            error_message = self.env._("The FBR submission failed unexpectedly: %s", error)
        # A failed payload stays downloadable from the order form instead of
        # piling up as attachments at each retry.
        if error_message:
            self._l10n_pk_edi_pos_mark_failed(error_message)
            return
        self.write({
            'l10n_pk_edi_pos_state': 'successful' if mode == 'prod' else 'successful_demo',
            'l10n_pk_edi_pos_invoice_number': response['InvoiceNumber'],
            'l10n_pk_edi_pos_qr': response['InvoiceNumber'],
            'l10n_pk_edi_pos_error': False,
        })
        self._l10n_pk_edi_pos_post_payload(payload)

    def _l10n_pk_edi_pos_mark_failed(self, error_message):
        self.write({
            'l10n_pk_edi_pos_state': 'unsuccessful',
            'l10n_pk_edi_pos_error': error_message,
            'to_invoice': False,
        })

    def action_l10n_pk_edi_pos_resend(self):
        for order in self.filtered(lambda o: o.l10n_pk_edi_pos_state not in DONE_STATES):
            order._l10n_pk_edi_pos_send()

    def action_pos_order_paid(self):
        result = super().action_pos_order_paid()
        if self.config_id.l10n_pk_edi_pos_enabled and self.country_code == 'PK' and self.l10n_pk_edi_pos_state not in DONE_STATES:
            self._l10n_pk_edi_pos_send()
        return result

    def _l10n_pk_edi_pos_post_payload(self, payload):
        self.ensure_one()
        dump = json.dumps(payload, indent=4, default=str)
        self.message_post(
            body=self.env._("The FBR accepted this order under invoice number %s.", self.l10n_pk_edi_pos_invoice_number),
            attachments=[(f"FBR Request {self._l10n_pk_edi_pos_usin()}.json", dump.encode())],
        )
