# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import markupsafe
import requests

from datetime import datetime
from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import json_float_round
from odoo.tools.image import image_data_uri

DEFAULT_ENDPOINT = 'https://gw.fbr.gov.pk/DigitalInvoicing/v1/PostInvoiceData_v1'
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pk_edi_state = fields.Selection(
        string="E-Invoice(FBR) State",
        selection=[
            ('being_sent', "Being Sent To FBR"),
            ('processing', "Invoice is Processing"),
            ('sent', "Invoice Filed to FBR"),
            ('rejected', "Invoice Rejected"),
        ],
        copy=False, tracking=True, readonly=True,
    )
    l10n_pk_edi_header = fields.Html(
        help="User description of the current state, with hints to make the flow progress",
        copy=False, readonly=True,
    )
    l10n_pk_edi_show_send_to_fbr = fields.Boolean(
        string="Show Send to FBR button on view?",
        compute='_compute_l10n_pk_edi_show_send_to_fbr',
    )
    l10n_pk_edi_fbr_inv_ref = fields.Char(string="FBR Refrence Number", copy=False, readonly=True)
    l10n_pk_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="FBR Attachment",
        compute=lambda self: self._compute_linked_attachment_id(
            'l10n_pk_edi_attachment_id',
            'l10n_pk_edi_attachment_file'
        ),
        depends=['l10n_pk_edi_attachment_file']
    )
    l10n_pk_edi_attachment_file = fields.Binary(string="FBR File", attachment=True, copy=False)

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    @api.depends('l10n_pk_edi_fbr_inv_ref')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self.filtered(lambda m: m.country_code == 'PK'):
            move.show_reset_to_draft_button = (
                not move.l10n_pk_edi_fbr_inv_ref
                and move.show_reset_to_draft_button
            )

    @api.depends('state')
    def _compute_l10n_pk_edi_show_send_to_fbr(self):
        for move in self:
            move.l10n_pk_edi_show_send_to_fbr = (
                move._l10n_pk_edi_get_default_enable()
                and move.l10n_pk_edi_state != 'sent'
            )

    # -------------------------------------------------------------------------
    # E-Invocing Reports
    # -------------------------------------------------------------------------

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.company_id.country_id.code == 'PK' and self.l10n_pk_edi_fbr_inv_ref:
            return 'l10n_pk_edi.l10n_pk_edi_report_invoice_document_inherit'
        return super()._get_name_invoice_report()

    def _get_l10n_pk_edi_qr_code(self):
        self.ensure_one()
        barcode = False
        if self.l10n_pk_edi_fbr_inv_ref:
            barcode = self.env['ir.actions.report'].barcode(
                barcode_type='QR',
                value=self.l10n_pk_edi_fbr_inv_ref,
                width=120,
                height=120
            )
            barcode = image_data_uri(base64.b64encode(barcode))
        return barcode

    # -------------------------------------------------------------------------
    # Business actions
    # -------------------------------------------------------------------------

    def button_draft(self):
        # EXTENDS 'account'
        self.l10n_pk_edi_state = False
        return super().button_draft()

    def action_l10n_pk_edi_send(self):
        """
            Create a attachment and Send the invoice to the FBR.
        """

        self.ensure_one()

        if alerts := self._l10n_pk_edi_validate():
            alert_msg = "\n".join(("- " + alert.get('message', '')) for alert in alerts.values())
            raise ValidationError(_(
                "The invoices you're trying to send have incomplete or incorrect data.\n"
                "Please verify before sending.\n\n%s",
                alert_msg
            ))

        attachment_vals = self._l10n_pk_edi_get_attachment_values()
        self.env['ir.attachment'].create(attachment_vals)
        self.invalidate_recordset(fnames=['l10n_pk_edi_attachment_id', 'l10n_pk_edi_attachment_file'])
        self.message_post(attachment_ids=self.l10n_pk_edi_attachment_id.ids)
        self._l10n_pk_edi_send({self: attachment_vals})
        self.is_move_sent = True

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _l10n_pk_edi_validate(self):
        """
            This function validates the partners, move_lines, moves and other related parameters
            involved in the sending activity. It returns a dictionary of errors to indicate any
            issues that require attention.
        """

        alerts = {}
        alerts.update({
            **(self.partner_id + self.company_id.partner_id)._l10n_pk_edi_export_check(),
            **self.mapped('invoice_line_ids.product_id')._l10n_pk_edi_export_check(),
            **self._l10n_pk_edi_export_check(),
            **self.mapped('company_id')._l10n_pk_edi_export_check()
        })
        return alerts

    def _l10n_pk_edi_export_check(self):
        """
            Validating Invoices for E-Invoicing Compliance
        """

        def _group_by_error_code(move):
            if move.move_type in ['in_refund', 'out_refund'] and not move.ref:
                return 'missing_cancel_reason'
            return False

        error_messages = {
            'missing_cancel_reason': _(
                "Invoice(s) should have an Cancel Reason and Cancel Remarks if they are Credit/Debit Note."
            ),
        }
        return {
            f"l10n_pk_edi_{error_code}": {
                'level': 'danger',
                'message': error_messages[error_code],
                'action_text': _("View Invoice(s)"),
                'action': moves._get_records_action(name=_("Check Invoice(s)")),
            }
            for error_code, moves in self.grouped(_group_by_error_code).items()
            if error_code
        }

    # -------------------------------------------------------------------------
    # Tax Methods
    # -------------------------------------------------------------------------

    def _get_l10n_pk_edi_tax_values(self, line_tax_details):
        sales_tax_total = 0.0
        withhold_tax_total = 0.0
        extra_tax_total = 0.0
        sale_group_ids = self._get_l10n_pk_edi_sales_groups().ids
        withhold_group_ids = self._get_l10n_pk_edi_withhold_groups().ids
        tax_lines = self._get_l10n_pk_edi_tax_details_by_line(
            line_tax_details.get('tax_details', {})
        )
        for tax_group_id in tax_lines:
            if tax_group_id in sale_group_ids:
                sales_tax_total += tax_lines[tax_group_id]['amount']
            elif tax_group_id in withhold_group_ids:
                withhold_tax_total += tax_lines[tax_group_id]['amount']
            else:
                extra_tax_total += tax_lines[tax_group_id]['amount']
        return sales_tax_total, withhold_tax_total, extra_tax_total

    def _get_l10n_pk_edi_tax_details_by_line(self, tax_details):
        l10n_pk_tax_details = {}
        for tax_detail in tax_details.values():
            line_code = tax_detail['tax'].tax_group_id.id
            l10n_pk_tax_detail = l10n_pk_tax_details.get(line_code, {})
            l10n_pk_tax_detail.update(dict.fromkeys(('rate', 'amount', 'amount_currency'), 0.0))
            l10n_pk_tax_detail['rate'] += tax_detail['tax'].amount
            l10n_pk_tax_detail['amount'] += tax_detail['tax_amount']
            l10n_pk_tax_detail['amount_currency'] += tax_detail['tax_amount_currency']
            l10n_pk_tax_details[line_code] = l10n_pk_tax_detail
        return l10n_pk_tax_details

    # -------------------------------------------------------------------------
    # E-Invocing Methods
    # -------------------------------------------------------------------------
        
    def _get_l10n_pk_edi_sales_groups(self):
        return self.env['account.tax.group'].browse([
            sale_group_id
            for ref in (
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
            )
            if (sale_group_id := self.env['ir.model.data']._xmlid_to_res_model_res_id(
                f'account.{self.company_id.id}_{ref}'
            )[1])
        ])

    def _get_l10n_pk_edi_withhold_groups(self):
        return self.env['account.chart.template'].with_company(self.company_id).ref('tax_group_pk_wt')

    def _l10n_pk_edi_get_default_enable(self):
        self.ensure_one()
        is_taxable = (
            self._get_l10n_pk_edi_sales_groups()
            & self.line_ids.tax_ids.tax_group_id
        )
        return (
            self.state == 'posted'
            and self.company_id.account_fiscal_country_id.code == 'PK'
            and self.journal_id.type in ['sale', 'purchase']
            and self.l10n_pk_edi_state in (False, 'rejected')
            and is_taxable
        )

    def _l10n_pk_edi_format_timestamp(self, d):
        return datetime(d.year, d.month, d.day).isoformat(timespec='milliseconds') + 'Z'

    def _l10n_pk_edi_round_value(self, amount, precision_digits=2):
        """
            This method is call for rounding.
            If anything is wrong with rounding then we quick fix in method
        """
        return json_float_round(amount, precision_digits)

    def _l10n_pk_edi_is_global_discount(self, line):
        if not line.tax_ids and line.price_subtotal < 0:
            return True
        return False

    def _get_l10n_pk_edi_invoice_type(self):
        return {
            'in_invoice': 1,
            'out_invoice': 2,
            'in_refund': 3,
            'out_refund': 4,
        }.get(self.move_type)

    def _get_l10n_pk_edi_fbr_ref_number(self):
        if self.move_type in ['in_refund', 'out_refund']:
            return self.reversed_entry_id.l10n_pk_edi_fbr_inv_ref
        return False

    def _get_l10n_pk_edi_partner_address(self, partner):
        address = (
            partner.street or '',
            partner.street2 or '',
            partner.city or '',
            partner.state_id.name or '',
            f'Pin: {partner.zip}' if partner.zip else ''
        )
        return ', '.join(part for part in address if part)

    def _get_l10n_pk_edi_total_discount(self, lines):
        # Calculate the total discount as the sum of the global discount and the line discounts
        sign = 1 if self.is_inbound() else -1
        global_discount_line = lines.grouped(
            self._l10n_pk_edi_is_global_discount
        ).get(True, self.env['account.move.line'])
        lines = lines - global_discount_line
        global_discount = sum(line.balance for line in global_discount_line) * sign
        lines_discount = sum((line.price_unit * line.quantity) * (line.discount / 100) for line in lines)
        return global_discount + lines_discount

    def _get_l10n_pk_edi_line_details(self, lines, tax_details_per_record):
        move_line_payload = []
        uom_selection = dict(
            self.env['uom.uom']._fields['l10n_pk_uom_code']._description_selection(self.env)
        )
        sale_type_selection = dict(
            self.env['product.template']._fields['l10n_pk_edi_sale_type']._description_selection(self.env)
        )
        for line in lines:
            move_id = line.move_id
            product_id = line.product_id
            sale_value = line.balance * (1 if move_id.is_outbound() else -1)
            quantity = line.quantity or 0.0
            line_tax_details = tax_details_per_record.get(line, {})
            sales_tax_total, withhold_tax_total, extra_tax_total = self._get_l10n_pk_edi_tax_values(line_tax_details)
            line_discount = (line.price_unit * quantity) * line.discount / 100
            sale_type = product_id.l10n_pk_edi_sale_type if product_id.l10n_pk_edi_sale_type else ''
            line_json = {
                'hsCode': product_id.l10n_pk_edi_hs_code[:4],
                'productCode': product_id.code or '',
                'productDescription': (product_id.display_name or line.name).replace('\n', ''),
                'rate': self._l10n_pk_edi_round_value(line.price_unit),
                'uoM': uom_selection[line.product_uom_id.l10n_pk_uom_code],
                'quantity': self._l10n_pk_edi_round_value(quantity),
                'valueSalesExcludingST': self._l10n_pk_edi_round_value(sale_value + line_discount),
                'salesTaxApplicable': self._l10n_pk_edi_round_value(sales_tax_total),
                'retailPrice': self._l10n_pk_edi_round_value(product_id.list_price),
                'salesTaxWithheldAtSource': 0.0,
                'extraTax': self._l10n_pk_edi_round_value(extra_tax_total),
                'furtherTax': 0.0,
                'sroScheduleNo': '',
                'fedPayable': 0.0,
                'cvt': 0.0,
                'withholdingIncomeTaxApplicable': self._l10n_pk_edi_round_value(withhold_tax_total),
                'whiT_1': 0.0,
                'whiT_2': 0.0,
                'whiT_Section_1': '',
                'whiT_Section_2': '',
                'totalValues': self._l10n_pk_edi_round_value(sale_value + sales_tax_total),
                'discount': self._l10n_pk_edi_round_value(line_discount),
                'stWhAsWhAgent': 0,
                'sroItemSerialNo': (
                    product_id.l10n_pk_edi_schedule_code[-3:]
                    if product_id.l10n_pk_edi_schedule_code else ''
                ),
                'purchaseType': (
                    sale_type_selection[product_id.l10n_pk_edi_sale_type]
                    if move_id.is_purchase_document(include_receipts=True) else ''
                ),
                'saleType': (
                    sale_type_selection[product_id.l10n_pk_edi_sale_type]
                    if move_id.is_sale_document(include_receipts=True) else ''
                ),
            }
            if reference_number := self._get_l10n_pk_edi_fbr_ref_number():
                line_json['invoiceRefNo'] = reference_number
            move_line_payload.append(line_json)
        return move_line_payload

    def _l10n_pk_edi_generate_invoice_json(self):

        def _get_buyer_seller():
            if self.is_sale_document(include_receipts=True):
                return self.partner_id, self.company_id.partner_id
            elif self.is_purchase_document(include_receipts=True):
                return self.company_id.partner_id, self.partner_id

        buyer, seller = _get_buyer_seller()
        tax_details = self._prepare_invoice_aggregated_taxes()
        tax_details_per_record = tax_details.get('tax_details_per_record')
        lines = self.invoice_line_ids.grouped(lambda line: line.display_type not in (
            'line_note', 'line_section', 'rounding'
        )).get(True, self.env['account.move.line'])
        total_discount = self._get_l10n_pk_edi_total_discount(lines)
        lines -= lines.grouped(
            self._l10n_pk_edi_is_global_discount
        ).get(True, self.env['account.move.line'])
        # Total Sale Value (Excluding Discount and Tax Amount)
        total_sale_value = sum(line.price_unit * line.quantity for line in lines)
        total_tax_value = tax_details.get('tax_amount')
        json_payload = {
            'bposid': self.company_id.l10n_pk_edi_pos_key,
            'invoiceType': self._get_l10n_pk_edi_invoice_type(),
            'invoiceDate': self._l10n_pk_edi_format_timestamp(self.invoice_date),
            'sellerNTNCNIC': self.company_id.vat,
            'sellerProvince': seller.state_id.name,
            'sellerBusinessName': seller.name,
            'businessDestinationAddress': self._get_l10n_pk_edi_partner_address(seller),
            'buyerNTNCNIC': buyer.vat or '',
            'buyerBusinessName': buyer.name or '',
            'buyerProvince': buyer.state_id.name,
            'saleType': 'T1000017',
            'salesValue': self._l10n_pk_edi_round_value(total_sale_value + total_tax_value - total_discount),
            'totalSalesTaxApplicable': self._l10n_pk_edi_round_value(total_tax_value),
            'totalRetailPrice': self._l10n_pk_edi_round_value(sum(line.price_unit for line in lines)),
            'totalSTWithheldAtSource': 0.0,
            'totalExtraTax': 0.0,
            'totalFEDPayable': 0.0,
            'totalWithholdingIncomeTaxApplicable': 0.0,
            'totalCVT': 0.0,
            'totalDiscount': self._l10n_pk_edi_round_value(total_discount),
            'items': self._get_l10n_pk_edi_line_details(lines, tax_details_per_record),
        }
        if reference_number := self._get_l10n_pk_edi_fbr_ref_number():
            json_payload['reason'] = self.ref
            json_payload['invoiceRefNo'] = reference_number
        return json_payload

    def _l10n_pk_edi_get_attachment_values(self):
        self.ensure_one()
        return {
            'name': f'{self.name.replace("/", "_")}_fbr_content.json',
            'type': 'binary',
            'mimetype': 'application/json',
            'description': f'EDI e-move: {self.move_type}',
            'company_id': self.company_id.id,
            'res_id': self.id,
            'res_model': self._name,
            'res_field': 'l10n_pk_edi_attachment_file',
            'raw': json.dumps(self._l10n_pk_edi_generate_invoice_json()),
        }

    def _l10n_pk_edi_send(self, attachments_vals):
        files_to_upload = []
        filename_move = {}
        for move in self:
            move.l10n_pk_edi_header = False
            move.l10n_pk_edi_state = 'being_sent'
            files_to_upload.append({
                'id': move.id,
                'name': move.name,
                'json': json.loads(attachments_vals[move]['raw'])
            })
            filename_move[move.name] = move

        """
            Example response with no errors
            {
                '$id': '1',
                'version': '1.0',
                'statusCode': 200,
                'errorMessage': '',
                'result': '900005CLNP5914173522',
                'timestamp': '2023-12-20T16:59:15',
                'errors': {
                    '$id': '2',
                    '$values': []
                }
            }

            Example response with error messages and details in the `errorMessage`
            field and the `errors['$values']` array.
            {
                '$id': '1',
                'version': '1.0',
                'statusCode': 200,
                'errorMessage': 'Invalid BPOSID Not Found!',
                'result': '',
                'timestamp': '2024-08-30T13:35:42',
                'errors': {
                    '$id': '2',
                    '$values': [
                        'The SellerNTNCNIC field is required.',
                        'The SellerProvince field is required.'
                    ]
                }
            }
        """

        results = self._l10n_pk_edi_generate(files_to_upload)
        for move_name in filename_move:
            move = filename_move[move_name]
            response = results[move_name]
            if (
                response.get('fault')
                or response.get('errorMessage')
                or response.get('errors', {}).get('$values')
            ):
                error_response = []
                if response.get('fault'):
                    error_response.append(response.get('fault').get('description'))
                if response.get('errorMessage'):
                    error_response.extend(response.get('errorMessage').split(','))
                if response.get('errors') and response.get('errors').get('$values'):
                    error_response.extend(response.get('errors').get('$values'))

                error_response = "<br/>".join(f"- {err}" for err in error_response)
                error_response = _(
                    "Error uploading the e-invoice as mentioned below:<br/>%(error)s",
                    error=error_response
                )
                error = _(
                    "Error uploading the e-invoice file %(name)s.\n%(error)s",
                    name=move_name,
                    error=error_response.replace('<br/>', '\n'),
                )
                move.sudo().message_post(body=error)
                move.l10n_pk_edi_header = error_response
                move.l10n_pk_edi_state = 'rejected'
                attachment = self.env['ir.attachment'].create(
                    {
                        'name': ('FBR-response:', move.name),
                        'res_id': move.id,
                        'res_model': move._name,
                        'type': 'binary',
                        'raw': json.dumps(response),
                        'mimetype': 'application/json'
                    }
                )
            else:
                message = (_("The e-invoice for %s was successfully sent to the FBR.", move_name))
                move.l10n_pk_edi_header = False
                move.l10n_pk_edi_state = 'sent'
                move.l10n_pk_edi_fbr_inv_ref = response.get('result')
                move.sudo().message_post(body=message)

    # -------------------------------------------------------------------------
    # API Methods
    # -------------------------------------------------------------------------

    def _l10n_pk_edi_connect_to_server(self, moves_json):
        results = {}
        session = requests.Session()
        for move_json in moves_json:
            try:
                results[move_json['name']] = session.post(
                    DEFAULT_ENDPOINT,
                    json=move_json['json'],
                    headers={
                        'Authorization': f'Bearer {self.company_id.sudo().l10n_pk_edi_token}',
                        'Content-Type': 'application/json',
                    },
                    timeout=25,
                ).json()
            except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
                _logger.warning('Connection error: %s', e.args[0])
                results[move_json['name']] = {
                    'statusCode': 404,
                    'errorMessage': _("Unable to connect to the online E-invoice(Pakistan) service. "
                        "The web service may be temporary down. Please try again in a moment."
                    )
                }
        return results

    def _l10n_pk_edi_generate(self, moves_json):
        # Avoid requesting to API(s) if user uses testing credentials
        if self.company_id.sudo().l10n_pk_edi_token == '906b1cd8-0d10-3a91-8234-8ec88e376bd6':
            results = {}
            for move_json in moves_json:
                # Return a response indicating success for all moves in `moves_json`
                results[move_json['name']] = {
                    '$id': '1',
                    'version': '1.0',
                    'statusCode': 200,
                    'errorMessage': '',
                    'result': '123456DUMMY987654321',
                    'timestamp': self._l10n_pk_edi_format_timestamp(datetime.now()),
                    'errors': {
                        '$id': '2',
                        '$values': []
                    }
                }
            return results
        return self._l10n_pk_edi_connect_to_server(moves_json)
