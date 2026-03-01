import json
from collections import defaultdict

from werkzeug.urls import url_encode

from odoo import api, fields, models
from odoo.tools.binary import BinaryBytes
from odoo.tools.float_utils import json_float_round
from odoo.tools.image import image_data_uri

ROUNDING_PRECISION_DIGITS = 2
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

    l10n_pk_edi_status_message = fields.Html(string='Status Message', copy=False, readonly=True, help='User description of the current state, with hints to make the flow progress')
    l10n_pk_edi_reference = fields.Char(string='FBR Reference Number', copy=False, readonly=True, tracking=True, help='Unique reference number assigned by FBR for the submitted invoice.')
    l10n_pk_edi_refund_reason = fields.Char(string='Refund Reason', copy=False, help='Reason for cancellation or refund of the e-invoice, as reported to FBR.')
    l10n_pk_edi_attachment_file = fields.Binary(string='FBR JSON File', attachment=True, copy=False, readonly=True)
    l10n_pk_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='FBR Attachment',
        compute=lambda self: self._compute_linked_attachment_id('l10n_pk_edi_attachment_id', 'l10n_pk_edi_attachment_file'),
        copy=False, readonly=True)
    l10n_pk_edi_status = fields.Selection(
        selection=[
            ('to_send', 'To Send'),
            ('sent', 'Valid'),
            ('failed', 'Invalid'),
            ('sent_test', 'Valid (Test)'),
        ],
        string='E-Invoice Status',
        default='to_send',
        copy=False,
        readonly=True,
        tracking=True,
    )
    l10n_pk_edi_testing_scenario_type = fields.Selection(
        selection=[
            ('SN001', 'SN001 - Sale of Standard Rate Goods to Registered Buyers'),
            ('SN002', 'SN002 - Sale of Standard Rate Goods to Unregistered Buyers'),
            ('SN003', 'SN003 - Sale of Steel (Melted and Re-Rolled) (Billets, Ingots and Long Bars)'),
            ('SN004', 'SN004 - Sale of Steel Scrap by Ship Breakers'),
            ('SN005', 'SN005 - Sales of Reduced Rate Goods (Eighth Schedule)'),
            ('SN006', 'SN006 - Sale of Exempt Goods (Sixth Schedule)'),
            ('SN007', 'SN007 - Sale Of Zero-Rated Goods (Fifth Schedule)'),
            ('SN008', 'SN008 - Sale of 3rd Schedule Goods'),
            ('SN009', 'SN009 - Purchase From Registered Cotton Ginners'),
            ('SN010', 'SN010 - Sale Of Telecom Services by Mobile Operators'),
            ('SN011', 'SN011 - Sale of Steel through Toll Manufacturing (Billets, Ingots and Long Bars)'),
            ('SN012', 'SN012 - Sale Of Petroleum Products'),
            ('SN013', 'SN013 - Sale Of Electricity to Retailers'),
            ('SN014', 'SN014 - Sale of Gas to CNG Stations'),
            ('SN015', 'SN015 - Sale of Mobile Phones'),
            ('SN016', 'SN016 - Processing / Conversion of Goods'),
            ('SN017', 'SN017 - Sale of Goods Where FED Is Charged in ST Mode'),
            ('SN018', 'SN018 - Sale Of Services Where FED Is Charged in ST Mode'),
            ('SN019', 'SN019 - Sale of Services (as per ICT Ordinance)'),
            ('SN020', 'SN020 - Sale of Electric Vehicles'),
            ('SN021', 'SN021 - Sale of Cement/Concrete Block'),
            ('SN022', 'SN022 - Sale of Potassium Chlorate'),
            ('SN023', 'SN023 - Sale of CNG'),
            ('SN024', 'SN024 - Sale Of Goods Listed in Statutory Regulatory Order 297(1)/2023'),
            ('SN025', 'SN025 - Drugs Sold at Fixed ST Rate Under Serial 81 Of Eighth Schedule Table 1'),
            ('SN026', 'SN026 - Sale Of Goods at Standard Rate to End Consumers by Retailers'),
            ('SN027', 'SN027 - Sale Of 3rd Schedule Goods to End Consumers by Retailers'),
            ('SN028', 'SN028 - Sale of Goods at Reduced Rate to End Consumers by Retailers'),
        ],
        string='FBR Sandbox Scenario',
        help='Select the appropriate FBR scenario for testing e-invoice submission in sandbox environment.',
    )
    l10n_pk_edi_test_environment = fields.Boolean(related='company_id.l10n_pk_edi_test_environment')
    l10n_pk_edi_enable = fields.Boolean(related='company_id.l10n_pk_edi_enable')
    l10n_pk_edi_json_response = fields.Binary(
        string='FBR JSON Response',
        attachment=True, copy=False, readonly=True,
        help='Pakistan: FBR response JSON, stored for debugging submission failures.',
    )
    l10n_pk_edi_json_response_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='FBR Response Attachment',
        compute=lambda self: self._compute_linked_attachment_id('l10n_pk_edi_json_response_id', 'l10n_pk_edi_json_response'),
        copy=False, readonly=True)

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

    @api.depends('l10n_pk_edi_reference')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        pk_moves = self.filtered(
            lambda move: move.company_id.account_fiscal_country_id.code == 'PK',
        )
        for move in pk_moves:
            move.show_reset_to_draft_button = (
                (move.l10n_pk_edi_testing_scenario_type or not move.l10n_pk_edi_reference) and move.show_reset_to_draft_button
            )

    # -------------------------------------------------------------------------
    # E-Invoicing Reports
    # -------------------------------------------------------------------------

    def _get_name_invoice_report(self):
        """Return the appropriate invoice report template for this record."""

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
                'danger',
                'l10n_pk_edi_cancel_reason_missing',
                self.env._('A cancellation reason is required for refunding or cancelling an e-invoice.'),
            )
        if not self.l10n_pk_edi_testing_scenario_type and self.l10n_pk_edi_test_environment:
            return (
                'danger',
                'l10n_pk_edi_scenario_type_missing',
                self.env._('A FBR Sandbox Scenario is required to send test e-invoice.'),
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
                    'action_text':  self.env._('View Invoice(s)'),
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
            and self.l10n_pk_edi_status in ('to_send', 'failed')
        )

    # -------------------------------------------------------------------------
    # Tax Methods
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_pk_edi_tax_details_by_line(self, tax_details):
        """Aggregate tax details by tax group."""
        aggregated_by_group = defaultdict(lambda: {'rate': 0.0, 'amount': 0.0})
        for tax_data in tax_details['taxes_data']:
            tax_total_group = tax_data['tax']._l10n_pk_edi_total_tax_group()
            aggregated_by_group[tax_total_group]['rate'] += tax_data['tax'].amount
            aggregated_by_group[tax_total_group]['amount'] += tax_data['tax_amount']
        return dict(aggregated_by_group)

    @api.model
    def _l10n_pk_edi_tax_values(self, move_line):
        """Calculate total sales, withholding, and extra tax from line tax details."""

        vals = {
            'sales_tax_rates': [],
            'sales_tax_total': 0.0,
            'further_tax_total': 0.0,
            'withholding_tax_total': 0.0,
        }

        base_lines = self._prepare_product_base_line_for_taxes_computation(move_line)
        self.env['account.tax']._add_tax_details_in_base_line(
            base_lines, self.company_id,
        )

        tax_lines = self._l10n_pk_edi_tax_details_by_line(base_lines.get('tax_details', {}))

        for tax_group, values in tax_lines.items():
            if tax_group == 'sales_tax_total':
                vals['sales_tax_rates'].append(values['rate'])
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
        self.invalidate_recordset(fnames=['l10n_pk_edi_attachment_id', 'l10n_pk_edi_attachment_file'])

    @api.model
    def _get_l10n_pk_edi_line_details(self, move_lines):
        """
        Build payload list for invoice lines.

        Returns:
            list[dict]: List of line payloads for EDI.
        """

        def _round(value, precision_digits=False):
            return json_float_round(value or 0.0, precision_digits or ROUNDING_PRECISION_DIGITS)

        move_lines_payload = []
        invoice_lines = move_lines.filtered(lambda line: line.display_type not in ('line_note', 'line_section', 'rounding'))
        uom_code_selection, sale_type_selection = (
            dict(self.env['product.template']._fields[field]._description_selection(self.env))
            for field in ('l10n_pk_edi_uom_code', 'l10n_pk_edi_sale_type')
        )
        custom_rate_tags = self._l10n_pk_edi_sale_type_custom_rate()
        for line in invoice_lines:
            product = line.product_id

            discount_amount = line.price_unit * line.quantity * line.discount / 100
            tax_values = self._l10n_pk_edi_tax_values(line)
            sales_tax_rates = tax_values.get('sales_tax_rates') or []
            rate = (
                custom_rate_tags.get(line.l10n_pk_edi_sale_type, False)
                or ",".join(f"{int(rate) if rate == int(rate) else rate}%" for rate in sales_tax_rates)if sales_tax_rates else ""
            )

            item_payload = {
                'hsCode': product.hs_code,
                'productDescription': (line.name or product.display_name or '').replace('\n', ' ')[:200],
                'rate': rate,
                'uoM': uom_code_selection.get(product.l10n_pk_edi_uom_code, 'Nos'),
                'quantity': _round(line.quantity, 4),
                'totalValues': _round(line.price_total),
                'valueSalesExcludingST': _round(line.price_subtotal),
                'fixedNotifiedValueOrRetailPrice': product.list_price * line.quantity if line.l10n_pk_edi_sale_type == '23' else "",
                'salesTaxApplicable': _round(tax_values.get('sales_tax_total')),
                'salesTaxWithheldAtSource': _round(tax_values.get('withholding_tax_total')),
                'extraTax': "",
                'furtherTax': _round(tax_values.get('further_tax_total')),
                'sroScheduleNo': line.l10n_pk_edi_sro_id.name,
                'fedPayable': 0.0,
                'discount': _round(discount_amount),
                'saleType': sale_type_selection.get(line.l10n_pk_edi_sale_type, 'Goods at standard rate'),
                'sroItemSerialNo': line.l10n_pk_edi_sro_item_id.name,
            }

            move_lines_payload.append(item_payload)

        return move_lines_payload

    @api.model
    def _l10n_pk_edi_sale_type_custom_rate(self):
        # Some Sale Types on the product require a custom rate tag
        return {
            '81': 'Exempt',
        }

    def _l10n_pk_edi_generate_invoice_json(self, extra_payload=None):
        """Generate the JSON payload for E-Invoices."""

        self.ensure_one()
        buyer = self.partner_id
        seller = self.company_id.partner_id
        seller_address = (seller._display_address() or '').replace('\n', ' ')
        buyer_address = (buyer._display_address() or '').replace('\n', ' ')
        fbr_customer_status_selection = dict(self.env['res.partner']._fields['l10n_pk_edi_fbr_customer_status']._description_selection(self.env))

        json_payload = {
            'invoiceType': self._get_l10n_pk_edi_invoice_type(),
            'invoiceDate': str(self.invoice_date),
            'invoiceTime': fields.Datetime.now().strftime('%H:%M:%S'),
            'invoiceRefNo': self.name or self.ref or 'INV-001',
            'invoiceTotalAmount': abs(self.amount_total),
            'sellerNTNCNIC': self.company_id.vat,
            'sellerBusinessName': seller.display_name,
            'sellerProvince': PROVINCE_FBR_NAMES.get(seller.state_id.code) or '',
            'sellerAddress': seller_address,
            'buyerNTNCNIC': buyer.vat if buyer.l10n_pk_edi_fbr_customer_status == 'registered' else '0000000',
            'buyerBusinessName': buyer.name,
            'buyerProvince': PROVINCE_FBR_NAMES.get(buyer.state_id.code) or '',
            'buyerAddress': buyer_address,
            'buyerRegistrationType': fbr_customer_status_selection[buyer.l10n_pk_edi_fbr_customer_status],
            'items': self._get_l10n_pk_edi_line_details(self.invoice_line_ids),
        }

        # Scenario ID is only used in sandbox mode
        if self.company_id.l10n_pk_edi_test_environment:
            json_payload['scenarioId'] = self.l10n_pk_edi_testing_scenario_type

        if self.move_type == 'out_invoice' and self.debit_origin_id and self.debit_origin_id.l10n_pk_edi_status == 'sent':
            json_payload['reason'] = self.l10n_pk_edi_refund_reason
            json_payload['invoiceRefNo'] = self.debit_origin_id.l10n_pk_edi_reference
            json_payload['invoiceRefNo'] = json_payload['invoiceRefNo'] + '*test*'

        if extra_payload:
            json_payload.update(extra_payload)

        return json_payload

    def _l10n_pk_edi_handle_response(self, response):
        """Apply a parsed FBR response to this move. Returns error_response dict or None."""
        result = self.env['iap.account']._l10n_pk_edi_parse_response(response)
        if result:
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
                (self.env._('Ensure NTN Number is set on company settings.')),
            )
        self.l10n_pk_edi_status_message = False

        # Prepare parameters
        params = {
            'auth_token': auth_token,
            'json_payload': json_payload,
        }
        is_production = not company.sudo().l10n_pk_edi_test_environment

        validate_res = self.env['iap.account']._l10n_pk_connect_to_server(is_production, params, '/api/l10n_pk_edi/1/validate')
        if error_response := self._l10n_pk_edi_handle_response(validate_res):
            self.l10n_pk_edi_json_response = BinaryBytes(json.dumps(validate_res).encode())
            return error_response
        posting_res = self.env['iap.account']._l10n_pk_connect_to_server(is_production, params, '/api/l10n_pk_edi/1/post')
        self.l10n_pk_edi_json_response = BinaryBytes(json.dumps(posting_res).encode())
        if error_response := self._l10n_pk_edi_handle_response(posting_res):
            return error_response

        # Success
        self.l10n_pk_edi_status = 'sent' if is_production else 'sent_test'
        self.l10n_pk_edi_status_message = False
        self.l10n_pk_edi_reference = posting_res.get('invoiceNumber')
        self.message_post(body=self.env._('The e-invoice was successfully sent to the FBR.'))
        self._l10n_pk_edi_create_attachment(json_payload)

        return False

    def download_l10n_pk_edi_json_response(self):
        params = url_encode({
            'model': self._name,
            'id': self.id,
            'field': 'l10n_pk_edi_json_response',
            'filename': f"{self.name.replace('/', '_')}_fbr_response.json",
            'mimetype': 'application/json',
            'download': 'true',
        })
        return {'type': 'ir.actions.act_url', 'url': '/web/content/?' + params, 'target': 'new'}
