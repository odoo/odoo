import base64
import json
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import json_float_round
from odoo.tools.image import image_data_uri

from collections import defaultdict
from markupsafe import Markup

from ..data.l10n_pk_edi_data import ERROR_CODES

ROUNDING_PRECISION_DIGITS = 2
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    l10n_pk_edi_status = fields.Selection(
        selection=[
            ('being_sent', "In Progress"),
            ('sent', "Accepted by FBR"),
            ('failed', "Failed to Send"),
            ('rejected', "Rejected by FBR"),
        ],
        string="E-Invoice Status",
        copy=False,
        readonly=True,
        tracking=True,
    )
    l10n_pk_edi_status_message = fields.Html(
        string="Status Message",
        copy=False,
        readonly=True,
        help="User description of the current state, with hints to make the flow progress",
    )
    l10n_pk_edi_reference = fields.Char(
        string="FBR Reference Number",
        copy=False,
        readonly=True,
        tracking=True,
        help="Unique reference number assigned by FBR for the submitted invoice.",
    )
    l10n_pk_edi_refund_reason = fields.Char(
        string="Refund Reason",
        copy=False,
        help="Reason for cancellation or refund of the e-invoice, as reported to FBR.",
    )
    l10n_pk_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="FBR Attachment",
        compute=lambda self: self._compute_linked_attachment_id(
            'l10n_pk_edi_attachment_id',
            'l10n_pk_edi_attachment_file',
        ),
        copy=False,
        readonly=True,
    )
    l10n_pk_edi_attachment_file = fields.Binary(
        string="FBR JSON File",
        attachment=True,
        copy=False,
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Compute/Utility Methods
    # -------------------------------------------------------------------------

    def button_draft(self):
        # EXTENDS 'account'
        res = super().button_draft()
        self.l10n_pk_edi_status = False
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
            lambda move: move.company_id.account_fiscal_country_id.code == 'PK'
        )
        for move in pk_moves:
            move.show_reset_to_draft_button = (
                not move.l10n_pk_edi_reference
                and move.show_reset_to_draft_button
            )

    # -------------------------------------------------------------------------
    # E-Invoicing Reports
    # -------------------------------------------------------------------------

    def _get_name_invoice_report(self):
        """Return the appropriate invoice report template for this record."""

        self.ensure_one()
        # Use PK E-Invoice report template once accepted by FBR
        if (
            self.company_id.country_id.code == 'PK'
            and self.l10n_pk_edi_status == 'sent'
            and self.l10n_pk_edi_reference
        ):
            return 'l10n_pk_edi.l10n_pk_edi_report_invoice_document_inherit'

        return super()._get_name_invoice_report()

    def _l10n_pk_edi_qr_code(self):
        """Return a QR code (data URI) for the FBR reference"""

        self.ensure_one()
        # Raise error if no FBR reference exists
        if not self.l10n_pk_edi_reference:
            raise ValidationError(self.env._(
                'No FBR reference number exists for the invoice.'
            ))

        # Generate QR code image bytes
        barcode_bytes = self.env['ir.actions.report'].barcode(
            barcode_type='QR',
            value=self.l10n_pk_edi_reference,
            humanReadable=True,
            width=120,
            height=120,
        )

        # Convert to base64-encoded image data URI
        return image_data_uri(base64.b64encode(barcode_bytes))

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_pk_edi_compose_error_response(self, error_code=None, messages=None):
        """Prepare a standardized error response."""

        # Normalize error message
        error_messages = messages or [
            self.env._("An unexpected error occurred while processing the request.")
        ]
        error_response = {'error': {
            'code': error_code or 'INTERNAL_SERVER_ERROR',
            'messages': error_messages,
        }}

        # Log full details for debugging
        _logger.error('PK EDI error response: %s', error_response)

        return error_response

    def _l10n_pk_edi_export_check(self):
        """Validate Invoice/Credit-Note for E-Invoicing compliance."""

        def _group_by_error_code(move):
            if move.move_type == 'out_refund' and not move.l10n_pk_edi_refund_reason:
                return 'cancel_reason_missing'
            return False

        error_messages = {
            'cancel_reason_missing': self.env._(
                "A cancellation reason is required for refunding or cancelling an e-invoice."
            ),
        }

        alerts = {}
        for error_code, invalid_record in self.grouped(_group_by_error_code).items():
            if not error_code:
                continue

            alerts[f'l10n_pk_edi_{error_code}'] = {
                'level': 'danger',
                'message': error_messages[error_code],
                'action_text': self.env._("View Invoice(s)"),
                'action': invalid_record._get_records_action(name=self.env._("Check Invoice(s)")),
            }

        return alerts

    def _l10n_pk_edi_validate(self):
        """Validate companies, partners, and products before sending to FBR."""

        companies = self.mapped('company_id')
        partners = self.partner_id | self.commercial_partner_id
        products = self.mapped('invoice_line_ids.product_id')

        return {
            **self._l10n_pk_edi_export_check(),
            **companies._l10n_pk_edi_export_check(),
            **partners._l10n_pk_edi_export_check(),
            **products._l10n_pk_edi_export_check(),
        }

    def _l10n_pk_edi_default_enable(self):
        """Check whether the invoice is eligible for PK E-Invoicing."""

        self.ensure_one()
        return (
            self.state == 'posted'
            and self.country_code == 'PK'
            and self.company_id.l10n_pk_edi_enable
            and self._get_l10n_pk_edi_invoice_type()
            and self.l10n_pk_edi_status in (False, 'failed', 'rejected')
        )

    # -------------------------------------------------------------------------
    # Tax Methods
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_pk_edi_tax_groups(self, company):
        """Return sales and withholding tax groups for the company."""

        # List of sales tax group IDs
        sales_tax_group_ids = [
            'tax_group_pk_0',
            'tax_group_pk_1',
            'tax_group_pk_2',
            'tax_group_pk_3',
            'tax_group_pk_5',
            'tax_group_pk_8',
            'tax_group_pk_10',
            'tax_group_pk_13',
            'tax_group_pk_15',
            'tax_group_pk_16',
            'tax_group_pk_17',
            'tax_group_pk_195',
        ]
        IrModelData = self.env['ir.model.data']

        # Fetch Sales tax group
        sales_tax_group_ids = [
            group for ref in sales_tax_group_ids
            if (group := IrModelData._xmlid_to_res_model_res_id(f'account.{company.id}_{ref}')[1])
        ]
        sales_tax_group = self.env['account.tax.group'].browse(sales_tax_group_ids)

        # Fetch Withholding tax group
        withhold_tax_group = self.env['account.chart.template']\
            .with_company(company)\
            .ref('tax_group_pk_wt')

        return sales_tax_group, withhold_tax_group

    @api.model
    def _l10n_pk_edi_tax_details_by_line(self, tax_details):
        """Aggregate tax details by tax group."""

        # Initialize container with default values for each tax group
        aggregated_by_group = defaultdict(lambda: {'rate': 0.0, 'amount': 0.0})

        # Loop through each tax detail and accumulate values per tax group
        for tax_data in tax_details['taxes_data']:
            tax_group = tax_data['tax'].tax_group_id.id
            aggregated_by_group[tax_group]['rate'] += tax_data['tax'].amount
            aggregated_by_group[tax_group]['amount'] += tax_data['tax_amount']

        return dict(aggregated_by_group)

    @api.model
    def _l10n_pk_edi_tax_values(self, move_line):
        """Calculate total sales, withholding, and extra tax from line tax details."""

        sales_tax_rates = []
        sales_tax_total = 0.0
        withhold_tax_total = 0.0
        extra_tax_total = 0.0

        # Fetch sales and withholding tax groups for the company
        sales_tax_group, withhold_tax_group = self._l10n_pk_edi_tax_groups(self.company_id)
        sale_groups = sales_tax_group.ids
        withhold_groups = withhold_tax_group.ids

        # Get tax details for particular invoice line
        base_lines = self._prepare_product_base_line_for_taxes_computation(move_line)
        self.env['account.tax']._add_tax_details_in_base_line(base_lines, self.company_id)

        # Get aggregated tax amounts grouped by tax group
        tax_lines = self._l10n_pk_edi_tax_details_by_line(
            base_lines.get('tax_details', {})
        )

        # Distribute tax amounts into respective totals
        for tax_group, values in tax_lines.items():
            if tax_group in sale_groups:
                sales_tax_rates.append(values['rate'])
                sales_tax_total += values['amount']
            elif tax_group in withhold_groups:
                withhold_tax_total += values['amount']
            else:
                extra_tax_total += values['amount']

        return {
            # Returning sales tax rates along with tax totals, as they are required in line details
            'sales_tax_rates': sales_tax_rates,
            'sales_tax_total': sales_tax_total,
            'withhold_tax_total': withhold_tax_total,
            'extra_tax_total': extra_tax_total,
        }

    # -------------------------------------------------------------------------
    # E-Invoicing Methods
    # -------------------------------------------------------------------------

    def _get_l10n_pk_edi_invoice_type(self):
        """Return the document type for E-Invoicing based on move type."""

        self.ensure_one()
        return {
            'out_invoice': 'Sales Invoice',
            'out_refund': 'Debit Note',  # According to FBR, Debit Note is used for `Sales Return``.
        }.get(self.move_type)

    def _l10n_pk_edi_attachment_name(self, is_fbr_response=False):
        """Return a safe filename for PK EDI attachments."""

        self.ensure_one()
        safe_name = self.name.replace('/', '_')
        name_suffix = 'fbr_response' if is_fbr_response else 'json_content'
        return f'{safe_name}_{name_suffix}.json'

    def _l10n_pk_edi_create_attachment(self, json_payload, is_fbr_response=False):
        """Create and attach a PK EDI JSON file to the invoice."""

        self.ensure_one()
        attachment_vals = {
            'name': self._l10n_pk_edi_attachment_name(is_fbr_response),
            'mimetype': 'application/json',
            'raw': json.dumps(json_payload),
            'res_model': self._name,
            'res_id': self.id,
            'res_field': (
                False if is_fbr_response else 'l10n_pk_edi_attachment_file'
            ),
            'type': 'binary',
        }

        # Create JSON attachment
        attachment = self.env['ir.attachment'].create(attachment_vals)

        if is_fbr_response:
            # Log FBR response in chatter
            self.with_context(no_new_invoice=True).message_post(
                attachment_ids=attachment.ids
            )
        else:
            # Refresh binary attachment fields
            self.invalidate_recordset(fnames=[
                'l10n_pk_edi_attachment_id',
                'l10n_pk_edi_attachment_file',
            ])

        return attachment

    @api.model
    def _get_l10n_pk_edi_line_details(self, move_lines):
        """
        Build payload list for invoice lines.

        Returns:
            list[dict]: List of line payloads for EDI.
        """

        def _round(value, precision_digits=False):
            # Round numeric values to EDI precision
            return json_float_round(value, precision_digits or ROUNDING_PRECISION_DIGITS)

        move_lines_payload = []
        invoice_lines = move_lines.filtered(
            lambda line: line.display_type not in ('line_note', 'line_section', 'rounding')
        )
        # For selection labels
        uom_code_selection, sale_type_selection = (
            dict(self.env['product.template']._fields[field]._description_selection(self.env))
            for field in ('l10n_pk_edi_uom_code', 'l10n_pk_edi_transaction_type')
        )

        for line in invoice_lines:
            product = line.product_id

            # Compute discount and tax values
            discount_amount = line.price_unit * line.quantity * line.discount / 100
            tax_values = self._l10n_pk_edi_tax_values(line)
            sales_tax_rates = tax_values['sales_tax_rates']

            # Prepare and append json payload for each line
            move_lines_payload.append({
                'hsCode': product.l10n_pk_edi_hs_code,
                'productDescription': (line.name or product.display_name).replace('\n', ''),
                'rate': ','.join(f'{rate}%' for rate in sales_tax_rates) if sales_tax_rates else '',
                'uoM': uom_code_selection[product.l10n_pk_edi_uom_code],
                'quantity': _round(line.quantity, 4),
                'totalValues': _round(line.price_total),
                'valueSalesExcludingST': _round(line.price_subtotal),
                'fixedNotifiedValueOrRetailPrice': _round(product.standard_price),
                'salesTaxApplicable': _round(tax_values['sales_tax_total']),
                'salesTaxWithheldAtSource': _round(tax_values['withhold_tax_total']),
                'extraTax': _round(tax_values['extra_tax_total']),
                'furtherTax': 0.0,
                'fedPayable': 0.0,
                'discount': _round(discount_amount),
                'saleType': sale_type_selection[product.l10n_pk_edi_transaction_type],
                'sroScheduleNo': None,
                'sroItemSerialNo': None,
            })

        return move_lines_payload

    def _l10n_pk_edi_generate_invoice_json(self):
        """Generate the JSON payload for E-Invoices."""

        self.ensure_one()
        buyer = self.partner_id
        seller = self.company_id.partner_id

        # Base JSON payload structure for E-Invoice(FBR)
        json_payload = {
            'invoiceType': self._get_l10n_pk_edi_invoice_type(),
            'invoiceDate': str(self.invoice_date),
            'sellerNTNCNIC': self.company_id.vat,
            'sellerBusinessName': seller.display_name,
            'sellerProvince': seller.state_id.name,
            'sellerAddress': seller._display_address(without_company=True),
            'buyerNTNCNIC': buyer._l10n_pk_edi_is_valid_vat() and buyer.vat or '',
            'buyerBusinessName': buyer.name,
            'buyerProvince': buyer.state_id.name,
            'buyerAddress': buyer._display_address(without_company=True),
            'buyerRegistrationType': buyer._l10n_pk_edi_is_valid_vat() and 'Registered' or 'Unregistered',
            'scenarioId': None,  # Reserved for FBR scenarios
            'items': self._get_l10n_pk_edi_line_details(self.invoice_line_ids),
        }

        # Add invoice reference number if its a refund entrie.
        if (
            self.move_type == 'out_refund'
            and self.reversed_entry_id
            and self.reversed_entry_id.l10n_pk_edi_status == 'sent'
        ):
            json_payload['reason'] = self.l10n_pk_edi_refund_reason
            json_payload['invoiceRefNo'] = self.reversed_entry_id.l10n_pk_edi_reference

        return json_payload

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

        def _is_error_in_response(response):
            """
            Detect server/connection errors or business validation errors
            in the FBR response and update EDI status accordingly.

            :return: Error response dict if an error is detected, otherwise None
            """

            # Server or connection error
            if error := response.get('error'):
                self.l10n_pk_edi_status = 'failed'
                error_msg = error.get('message') or error.get('messages', '')
                self.l10n_pk_edi_status_message = f"- {error_msg}"

                return response

            # Business validation error
            validation = response.get('validationResponse')
            if not validation or validation.get('status') == 'Valid':
                return None

            errors = []

            # Check for Invoice-level error
            if validation.get('errorCode') or validation.get('error'):
                errors.append(ERROR_CODES.get(validation['errorCode'], validation['error']))

            # Check for Line-level errors
            for invoice_status in validation.get('invoiceStatuses') or []:
                errors.append(ERROR_CODES.get(invoice_status['errorCode'], invoice_status['error']))

            self.l10n_pk_edi_status = 'rejected'
            self.l10n_pk_edi_status_message = Markup('- ') + Markup('<br>- ').join(errors)
            return self._l10n_pk_edi_compose_error_response('VALIDATION_ERROR', errors)

        self.ensure_one()
        company = self.company_id

        # Step 0: Generate invoice JSON
        json_payload = self._l10n_pk_edi_generate_invoice_json()

        # Step 1: Retrieve and validate authentication token
        auth_token = company.l10n_pk_edi_auth_token
        if not auth_token:
            return self._l10n_pk_edi_compose_error_response(
                'MISSING_AUTH_TOKEN',
                (self.env._("Ensure NTN Number is set on company settings.")),
            )

        # Step 2: Update fields before sending
        self.l10n_pk_edi_status = 'being_sent'
        self.l10n_pk_edi_status_message = False

        # Prepare parameters
        params = {
            'auth_token': auth_token,
            'json_payload': json_payload,
        }
        is_production = not company.sudo().l10n_pk_edi_test_environment

        # Step 3: Validate
        validate_res = self.env['iap.account']._l10n_pk_connect_to_server(
            is_production, params, '/api/l10n_pk_edi/1/validate'
        )
        if error_response := _is_error_in_response(validate_res):
            return error_response

        # Step 4: Post
        posting_res = self.env['iap.account']._l10n_pk_connect_to_server(
            is_production, params, '/api/l10n_pk_edi/1/post'
        )
        if error_response := _is_error_in_response(posting_res):
            return error_response

        # Step 5: Success
        self.l10n_pk_edi_status = 'sent'
        self.l10n_pk_edi_status_message = False
        self.l10n_pk_edi_reference = posting_res.get('invoiceNumber')
        self.message_post(body=self.env._('The e-invoice was successfully sent to the FBR.'))

        self._l10n_pk_edi_create_attachment(json_payload)
        self._l10n_pk_edi_create_attachment(posting_res, True)

        return False
