import json
import logging
from collections import defaultdict
from odoo import api, fields, models
from odoo.tools.float_utils import json_float_round
from odoo.tools.image import image_data_uri

_logger = logging.getLogger(__name__)

ROUNDING_PRECISION_DIGITS = 2
FBR_UOM_CODE_OTHERS = '88'
PROVINCE_FBR_NAMES = {
    "PK-JK": "AZAD JAMMU AND KASHMIR",
    "PK-BA": "BALOCHISTAN",
    "PK-GB": "GILGIT BALTISTAN",
    "PK-IS": "CAPITAL TERRITORY",
    "PK-KP": "KHYBER PAKHTUNKHWA",
    "PK-PB": "PUNJAB",
    "PK-SD": "SINDH",
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    l10n_pk_edi_status_message = fields.Html(string="Status Message", copy=False, readonly=True, help="User description of the current state, with hints to make the flow progress")
    l10n_pk_edi_reference = fields.Char(string="FBR Reference Number", copy=False, readonly=True, tracking=True, help="Unique reference number assigned by FBR for the submitted invoice.")
    l10n_pk_edi_refund_reason = fields.Char(string="Refund Reason", copy=False, help="Reason for cancellation or refund of the e-invoice, as reported to FBR.")
    l10n_pk_edi_attachment_file = fields.Binary(string="FBR JSON File", attachment=True, copy=False, readonly=True)
    l10n_pk_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="FBR Attachment",
        compute=lambda self: self._compute_linked_attachment_id('l10n_pk_edi_attachment_id', 'l10n_pk_edi_attachment_file'),
        depends=['l10n_pk_edi_attachment_file'],
        readonly=True,
        copy=False,
    )
    l10n_pk_edi_status = fields.Selection(
        selection=[
            ('to_send', "To Send"),
            ('sent', "Valid"),
            ('failed', "Invalid"),
            ('sent_test', "Valid (Test)"),
        ],
        string="E-Invoice Status",
        default='to_send',
        copy=False,
        readonly=True,
        tracking=True,
    )
    l10n_pk_edi_enable = fields.Boolean(related='company_id.l10n_pk_edi_enable')

    def button_draft(self):
        # EXTENDS 'account'
        res = super().button_draft()
        self.l10n_pk_edi_status = 'to_send'
        return res

    @api.model
    def _get_fields_to_detach(self):
        # EXTENDS 'account'
        fields_to_detach = super()._get_fields_to_detach()
        fields_to_detach.append('l10n_pk_edi_attachment_file')
        return fields_to_detach

    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        pk_moves = self.filtered(
            lambda move: move.show_reset_to_draft_button
            and move.company_id.account_fiscal_country_id.code == 'PK',
        )
        for move in pk_moves:
            if move.l10n_pk_edi_status != 'sent_test':
                continue
            move.show_reset_to_draft_button = (
                move.company_id._l10n_pk_edi_is_test_mode() or not move.l10n_pk_edi_reference
            )

    # -------------------------------------------------------------------------
    # E-Invoicing Reports
    # -------------------------------------------------------------------------

    def _get_name_invoice_report(self):
        """Return the appropriate invoice report template for this record."""
        # EXTENDS 'account'
        self.ensure_one()
        if self.company_id.country_id.code == 'PK' and self.l10n_pk_edi_enable:
            return 'l10n_pk_edi.report_invoice_document'
        return super()._get_name_invoice_report()

    def _l10n_pk_edi_qr_code(self):
        """Return a QR code (data URI) for the FBR reference"""
        self.ensure_one()
        barcode_bytes = self.env['ir.actions.report'].barcode(
            barcode_type='QR',
            value=self.l10n_pk_edi_reference or '',
            humanReadable=True,
            width=96,
            height=96,
        )
        return image_data_uri(barcode_bytes)

    def _generate_qr_code(self, silent_errors=False):
        # EXTENDS 'account'
        self.ensure_one()
        if self.company_id.country_code == 'PK' and self.l10n_pk_edi_enable and self.l10n_pk_edi_reference:
            return self._l10n_pk_edi_qr_code()
        return super()._generate_qr_code(silent_errors)

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _group_by_error_code(self):
        self.ensure_one()
        if self.move_type == 'out_invoice' and self.debit_origin_id and not self.l10n_pk_edi_refund_reason:
            return (
                ('message', self.env._("A cancellation reason is required for refunding or cancelling an e-invoice.")),
                ('error_code', 'l10n_pk_edi_cancel_reason_missing'),
                ('level', 'danger'),
            )
        return False

    def _l10n_pk_edi_export_check(self):
        """Validate Invoice/Credit-Note for E-Invoicing compliance."""
        alert_vals = {}
        for error_tuple, invalid_records in self.grouped(lambda m: m._group_by_error_code()).items():
            if not error_tuple:
                continue
            temp_dict = dict(error_tuple)
            alert_vals.update({
                temp_dict['error_code']: {
                    'message': temp_dict['message'],
                    'level': temp_dict['level'],
                    'action': invalid_records._get_records_action(),
                    'action_text':  self.env._("View Invoice(s)"),
                },
            })
        return alert_vals

    def _l10n_pk_edi_default_enable(self):
        """Check whether the invoice is eligible for PK E-Invoicing."""

        self.ensure_one()
        return (
            self.state == 'posted'
            and self.country_code == 'PK'
            and self.company_id.l10n_pk_edi_enable
            and self._get_l10n_pk_edi_invoice_type()
            and self.l10n_pk_edi_status in {'to_send', 'failed'}
        )

    # -------------------------------------------------------------------------
    # Tax Methods
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_pk_edi_tax_details_by_line(self, tax_details):
        """Aggregate tax details by tax group."""
        aggregated_by_group = defaultdict(lambda: {'rates': [], 'amount': 0.0})
        for tax_data in tax_details['taxes_data']:
            tax_total_group = tax_data['tax']._l10n_pk_edi_total_tax_group()
            aggregated_by_group[tax_total_group]['rates'].append(tax_data['tax'].amount)
            aggregated_by_group[tax_total_group]['amount'] += tax_data['tax_amount']
        return dict(aggregated_by_group)

    def _l10n_pk_edi_tax_values(self, move_line):
        """Calculate total sales, further and withholding tax from line tax details.

        Extra tax is an unhandled flow: nothing maps to it, so FBR is sent a constant.
        """

        self.ensure_one()
        vals = {
            'sales_tax_rates': [],
            'sales_tax_total': 0.0,
            'further_tax_total': 0.0,
            'withholding_tax_total': 0.0,
        }

        base_lines = self._prepare_product_base_line_for_taxes_computation(move_line)
        # l10n_account_withholding_tax strips withholding taxes from the computation unless the
        # base line opts in. They are safe to include: that module forces them to 'tax_excluded'
        # and forbids the 'group' and 'division' types, so they cannot disturb the other taxes.
        base_lines['calculate_withholding_taxes'] = True
        self.env['account.tax']._add_tax_details_in_base_line(
            base_lines, self.company_id,
        )

        tax_lines = self._l10n_pk_edi_tax_details_by_line(base_lines.get('tax_details', {}))

        for tax_group, values in tax_lines.items():
            if tax_group == 'sales_tax_total':
                # FBR expects one entry per sales tax on the line,
                # so the rates are kept apart here and joined into
                # the comma separated list it reads.
                vals['sales_tax_rates'] = values['rates']
            vals[tax_group] += values['amount']
        return vals

    # -------------------------------------------------------------------------
    # E-Invoicing Methods
    # -------------------------------------------------------------------------

    def _get_l10n_pk_edi_invoice_type(self):
        """Return the document type for E-Invoicing based on move type."""
        self.ensure_one()
        if self.move_type == 'out_invoice':
            return 'Sale Invoice' if not self.debit_origin_id else 'Debit Note'
        return ''

    def _l10n_pk_edi_attachment_name(self):
        """Return a safe filename for the invoice JSON attachment."""
        self.ensure_one()
        return f"{self.name.replace('/', '_')}_json_content.json"

    def _l10n_pk_edi_create_attachment(self, json_payload):
        """Create and attach the invoice JSON file to the invoice."""
        self.ensure_one()
        self.env['ir.attachment'].create({
            'name': self._l10n_pk_edi_attachment_name(),
            'mimetype': 'application/json',
            'raw': json.dumps(json_payload).encode(),
            'res_model': self._name,
            'res_id': self.id,
            'res_field': 'l10n_pk_edi_attachment_file',
            'type': 'binary',
        })

    def _get_l10n_pk_edi_line_details(self, move_lines):
        """
        Build payload list for invoice lines.

        Returns:
            list[dict]: List of line payloads for EDI.
        """

        def _round(value, precision_digits=False):
            return json_float_round(value or 0.0, precision_digits or ROUNDING_PRECISION_DIGITS)

        def _rate_tag(value):
            return f"{int(value) if value == int(value) else value}%"

        self.ensure_one()
        move_lines_payload = []
        invoice_lines = move_lines.filtered(lambda line: line.display_type not in {'line_note', 'line_section', 'rounding'})
        uom_code_selection = dict(self.env['uom.uom']._fields['l10n_pk_edi_uom_code']._description_selection(self.env))
        sale_type_selection = dict(self.env['account.move.line']._fields['l10n_pk_edi_sale_type']._description_selection(self.env))
        rate_overrides = self._l10n_pk_edi_sale_type_rate_overrides()
        for line in invoice_lines:
            product = line.product_id

            tax_values = self._l10n_pk_edi_tax_values(line)
            sales_tax_rates = tax_values['sales_tax_rates']
            is_third_schedule = line.l10n_pk_edi_sale_type == '23'
            retail_price_base = product.lst_price * line.quantity

            sales_tax_total = tax_values.get('sales_tax_total', 0.0)
            # 3rd Schedule goods are taxed on the printed retail price rather than on what they
            # actually sold for, so the nominal rate does not describe the line. The retail price
            # is entered tax-inclusive, so the rate has to be measured against it net of the tax
            # itself, otherwise 18% reads as 18/118 = 15.25%.
            net_retail_price = retail_price_base - sales_tax_total
            if is_third_schedule and net_retail_price > 0:
                rate = _rate_tag(self.currency_id.round(sales_tax_total / net_retail_price * 100))
            else:
                rate = rate_overrides.get(line.l10n_pk_edi_sale_type) or ",".join(_rate_tag(sales_tax_rate) for sales_tax_rate in sales_tax_rates)

            item_payload = {
                'hsCode': self._l10n_pk_edi_format_hs_code(product.hs_code),
                'productDescription': (line.name or product.display_name or '').replace('\n', ' ')[:200],
                'rate': rate,
                'uoM': uom_code_selection[line.product_uom_id.l10n_pk_edi_uom_code or FBR_UOM_CODE_OTHERS],
                'quantity': _round(line.quantity, 4),
                'totalValues': _round(line.price_total),
                'valueSalesExcludingST': _round(line.price_subtotal),
                'fixedNotifiedValueOrRetailPrice': _round(net_retail_price) if is_third_schedule else "",
                'salesTaxApplicable': _round(tax_values.get('sales_tax_total')),
                'salesTaxWithheldAtSource': _round(abs(tax_values['withholding_tax_total'])),
                'extraTax': "",
                'furtherTax': _round(tax_values.get('further_tax_total')),
                'sroScheduleNo': line.l10n_pk_edi_sro_id.name,
                'fedPayable': 0.0,
                'discount': _round(line.price_unit * line.quantity * line.discount / 100),
                'saleType': sale_type_selection.get(line.l10n_pk_edi_sale_type, 'Goods at standard rate'),
                'sroItemSerialNo': line.l10n_pk_edi_sro_item_id.name,
            }

            move_lines_payload.append(item_payload)

        return move_lines_payload

    @api.model
    def _l10n_pk_edi_sale_type_rate_overrides(self):
        # FBR expects a fixed label rather than a computed percentage in a line's `rate`
        # for a few sale types.
        return {
            '81': 'Exempt',
        }

    @api.model
    def _l10n_pk_edi_format_hs_code(self, hs_code):
        # FBR expects the HS Code as 4 digits, a dot, then 4 more digits (e.g. 0101.2100).
        digits = (hs_code or '').replace('.', '').replace(' ', '')
        return f"{digits[:4]}.{digits[4:]}" if digits else ''

    def _l10n_pk_edi_generate_invoice_json(self):
        """Generate the JSON payload for E-Invoices."""

        self.ensure_one()
        buyer = self.partner_id
        seller = self.company_id.partner_id
        fbr_customer_status_selection = dict(self.env['res.partner']._fields['l10n_pk_edi_fbr_customer_status']._description_selection(self.env))

        json_payload = {
            'invoiceType': self._get_l10n_pk_edi_invoice_type(),
            'invoiceDate': str(self.invoice_date),
            'invoiceTime': fields.Datetime.context_timestamp(self.with_context(tz='Asia/Karachi'), fields.Datetime.now()).strftime('%H:%M:%S'),
            'invoiceRefNo': self.name,
            'invoiceTotalAmount': abs(self.amount_total),
            'sellerNTNCNIC': self.company_id.vat.replace('-', ''),
            'sellerBusinessName': seller.display_name,
            'sellerProvince': PROVINCE_FBR_NAMES.get(seller.state_id.code) or '',
            'sellerAddress': (seller._display_address() or '').replace('\n', ' '),
            'buyerNTNCNIC': (buyer.vat or '').replace('-', '') if buyer.l10n_pk_edi_fbr_customer_status == 'registered' else '0000000',
            'buyerBusinessName': buyer.name,
            'buyerProvince': PROVINCE_FBR_NAMES.get(buyer.state_id.code) or '',
            'buyerAddress': (buyer._display_address() or '').replace('\n', ' '),
            'buyerRegistrationType': fbr_customer_status_selection[buyer.l10n_pk_edi_fbr_customer_status],
            'items': self._get_l10n_pk_edi_line_details(self.invoice_line_ids),
        }
        if is_test_mode := self.company_id._l10n_pk_edi_is_test_mode():
            # Scenario ID is only used in sandbox mode. It is set via the 'l10n_pk_edi.test_scenario_id' system
            # parameter (Settings > Technical > System Parameters) rather than on the invoice, so that Support
            # can drive FBR sandbox whitelisting scenarios without touching client invoice data.
            json_payload['scenarioId'] = self.env['ir.config_parameter'].sudo().get_str('l10n_pk_edi.test_scenario_id')

        if self.move_type == 'out_invoice' and self.debit_origin_id and self.debit_origin_id.l10n_pk_edi_status in {'sent', 'sent_test'}:
            json_payload['reason'] = self.l10n_pk_edi_refund_reason
            json_payload['invoiceRefNo'] = self.debit_origin_id.l10n_pk_edi_reference or ''
            if is_test_mode and json_payload['invoiceRefNo']:
                # The FBR sandbox rejects a reference that was already posted, so it must be suffixed.
                json_payload['invoiceRefNo'] += '*test*'

        return json_payload

    def _l10n_pk_edi_handle_response(self, response):
        """Apply a parsed FBR response to this move. Returns error_response dict or None."""
        if result := self.env['iap.account']._l10n_pk_edi_parse_response(response):
            self.l10n_pk_edi_status = result['status']
            self.l10n_pk_edi_status_message = result['message']
            return result['error_response']
        return None

    def _l10n_pk_edi_send(self):
        """Send the EDI JSON payload to FBR via IAP.

        Steps:
            1. Generate JSON payload for the move
            2. Validate the payload with the IAP service.
            3. Post the payload if validation succeeds.

        Returns: dict | bool:
            Error response (dict) if something fails
            or False if the invoice was successfully sent.
        """

        self.ensure_one()
        company = self.company_id
        json_payload = self._l10n_pk_edi_generate_invoice_json()
        auth_token = company._get_l10n_pk_edi_auth_token()
        if not auth_token:
            return self.env['iap.account']._l10n_pk_edi_compose_error_response(
                'MISSING_AUTH_TOKEN',
                (self.env._("Ensure Business Identification Number is set on company settings.")),
            )
        self.l10n_pk_edi_status_message = False

        # Prepare parameters
        params = {
            'auth_token': auth_token,
            'json_payload': json_payload,
        }
        is_production = not company._l10n_pk_edi_is_test_mode()
        _logger.info("FBR payload for %s: %s", self.name, json.dumps(json_payload))

        validate_res = self.env['iap.account']._l10n_pk_connect_to_server(is_production, params, '/api/l10n_pk_edi/1/validate')
        if error_response := self._l10n_pk_edi_handle_response(validate_res):
            _logger.warning(
                "FBR validation failed for %s: %s\npayload: %s",
                self.name, json.dumps(validate_res), json.dumps(json_payload),
            )
            return error_response
        posting_res = self.env['iap.account']._l10n_pk_connect_to_server(is_production, params, '/api/l10n_pk_edi/1/post')
        if error_response := self._l10n_pk_edi_handle_response(posting_res):
            _logger.warning(
                "FBR posting failed for %s: %s\npayload: %s",
                self.name, json.dumps(posting_res), json.dumps(json_payload),
            )
            return error_response
        _logger.info("FBR posting response for %s: %s", self.name, json.dumps(posting_res))

        # Success
        self.l10n_pk_edi_status = 'sent' if is_production else 'sent_test'
        self.l10n_pk_edi_status_message = False
        self.l10n_pk_edi_reference = posting_res.get('invoiceNumber')
        self.message_post(body=self.env._("The e-invoice was successfully sent to the FBR."))
        self._l10n_pk_edi_create_attachment(json_payload)

        return False
