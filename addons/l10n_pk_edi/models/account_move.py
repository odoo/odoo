# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import markupsafe
import requests

from datetime import datetime
from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import json_float_round

DEFAULT_ENDPOINT = 'https://gw.fbr.gov.pk/DigitalInvoicing/v1/PostInvoiceData_v1'
DEFAULT_TIMEOUT = 25
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
        readonly=True, copy=False,
    )
    l10n_pk_edi_show_send_to_fbr = fields.Boolean(
        compute='_compute_l10n_pk_edi_show_send_to_fbr',
        string="Show Send to FBR button on view?"
    )
    l10n_pk_edi_fbr_inv_ref = fields.Char(copy=False, string="FBR Refrence Number")
    l10n_pk_edi_cancel_reason = fields.Selection(selection=[
        ('1', "Duplicate"),
        ('2', "Data Entry Mistake"),
        ('3', "Order Cancelled"),
        ('4', "Others"),
    ], string="Cancel Reason(FBR)", copy=False)
    l10n_pk_edi_cancel_remarks = fields.Char(string="Cancel Remarks(FBR)", copy=False)
    l10n_pk_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="FBR Attachment",
        compute=lambda self: self._compute_linked_attachment_id(
            'l10n_pk_edi_attachment_id',
            'l10n_pk_edi_attachment_file'
        ),
        depends=['l10n_pk_edi_attachment_file']
    )
    l10n_pk_edi_attachment_file = fields.Binary(attachment=True, string="FBR File", copy=False)

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
    # Business actions
    # -------------------------------------------------------------------------

    def button_draft(self):
        # EXTENDS 'account'
        self.l10n_pk_edi_state = False
        return super().button_draft()

    def action_l10n_pk_edi_send(self):
        '''
            Create a attachment and Send the invoice to the FBR.
        '''

        self.ensure_one()

        if alerts := self._l10n_pk_edi_validate():
            alert_msg = "\n".join(("- " + alert.get('message', '')) for alert in alerts.values())
            raise ValidationError(_("The invoices you're trying to send have incomplete or incorrect data. \nplease verify before sending.\n\n%s", alert_msg))

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
        '''
            This function validates the partners, move_lines, moves and other related parameters
            involved in the sending activity. It returns a dictionary of errors to indicate any
            issues that require attention.
        '''

        self.ensure_one()

        def _get_buyer_seller(move):
            if move.is_sale_document(include_receipts=True):
                return move.partner_id, move.company_id.partner_id
            elif move.is_purchase_document(include_receipts=True):
                return move.company_id.partner_id, move.partner_id

        alerts = {}
        buyer, seller = _get_buyer_seller(self)
        products = self.invoice_line_ids.product_id

        seller_checks = ['partner_vat_missing', 'partner_vat_invalid', 'partner_full_address_missing']
        alerts.update({
            **buyer._l10n_pk_edi_export_check(),
            **seller._l10n_pk_edi_export_check(seller_checks),
            **products._l10n_pk_edi_export_check(),
            **self._l10n_pk_edi_export_check(),
            **self.company_id._l10n_pk_edi_export_check()
        })
        return alerts

    def _l10n_pk_edi_export_check(self, checks=None):
        if invalid_records := self.filtered(
            lambda record: record.move_type in ['in_refund', 'out_refund']
            and (not record.l10n_pk_edi_cancel_reason or not record.l10n_pk_edi_cancel_remarks)
        ):
            alerts = {}
            alerts['l10n_pk_edi_missing_cancel_reason'] = {
                'level': 'danger',
                'message': _("Invoice(s) should have an Cancel Reason and Cancel Remarks if they are Credit/Debit Note."),
                'action_text': _("View Invoice(s)"),
                'action': invalid_records._get_records_action(name=_("Check Invoice(s)")),
            }
            return alerts
        return {}

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
        '''
            This method is call for rounding.
            If anything is wrong with rounding then we quick fix in method
        '''
        return json_float_round(amount, precision_digits)

    def _l10n_pk_edi_is_global_discount(self, line):
        return not line.tax_ids and line.price_subtotal < 0

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
        global_discount_line = lines.filtered(self._l10n_pk_edi_is_global_discount)
        lines = lines - global_discount_line
        global_discount = sum(line.balance for line in global_discount_line) * sign
        lines_discount = sum((line.price_unit * line.quantity) * (line.discount / 100) for line in lines)
        return global_discount + lines_discount

    def _get_l10n_pk_edi_line_details(self, line, line_tax_details):
        move_id = line.move_id
        product_id = line.product_id
        sale_value = line.balance * (1 if move_id.is_outbound() else -1)
        quantity = line.quantity or 0.0
        sales_tax_total, withhold_tax_total, extra_tax_total = self._get_l10n_pk_edi_tax_values(line_tax_details)
        line_discount = (line.price_unit * quantity) * line.discount / 100
        line_json = {
            'hsCode': product_id.l10n_pk_edi_hs_code,
            'productCode': product_id.code or '',
            'productDescription': (product_id.display_name or line.name).replace('\n', ''),
            'rate': self._l10n_pk_edi_round_value(line.price_unit),
            'uoM': line.product_uom_id.l10n_pk_uom_code or 'U1000088',
            'quantity': self._l10n_pk_edi_round_value(quantity),
            'valueSalesExcludingST': self._l10n_pk_edi_round_value(sale_value + line_discount),
            'salesTaxApplicable': self._l10n_pk_edi_round_value(sales_tax_total),
            'retailPrice': self._l10n_pk_edi_round_value(product_id.list_price),
            'salesTaxWithheldAtSource': 0.0,
            'extraTax': self._l10n_pk_edi_round_value(extra_tax_total),
            'furtherTax': 0.0,
            'sroScheduleNo': None,
            'fedPayable': 0.0,
            'cvt': 0.0,
            'withholdingIncomeTaxApplicable': self._l10n_pk_edi_round_value(withhold_tax_total),
            'whiT_1': 0.0,
            'whiT_2': None,
            'whiT_Section_1': None,
            'whiT_Section_2': '0.0',
            'totalValues': self._l10n_pk_edi_round_value(sale_value + sales_tax_total),
            'discount': self._l10n_pk_edi_round_value(line_discount),
            'sroItemSerialNo': (
                product_id.l10n_pk_edi_schedule_code
                if product_id.l10n_pk_edi_schedule_code else ''
            ),
            'stWhAsWhAgent': 0,
        }
        line_json[
            'saleType' if move_id.is_sale_document() else 'purchaseType'
        ] = product_id.l10n_pk_edi_sale_type if product_id.l10n_pk_edi_sale_type else ''
        if reference_number := self._get_l10n_pk_edi_fbr_ref_number():
            line_json['invoiceRefNo'] = reference_number
        return line_json

    def _l10n_pk_edi_generate_invoice_json(self):

        def _get_buyer_seller():
            if self.is_sale_document(include_receipts=True):
                return self.partner_id, self.company_id.partner_id
            elif self.is_purchase_document(include_receipts=True):
                return self.company_id.partner_id, self.partner_id

        buyer, seller = _get_buyer_seller()
        tax_details = self._prepare_invoice_aggregated_taxes()
        tax_details_per_record = tax_details.get('tax_details_per_record')
        lines = self.invoice_line_ids.filtered(lambda line: line.display_type not in (
            'line_note', 'line_section', 'rounding'
        ))
        total_discount = self._get_l10n_pk_edi_total_discount(lines)
        lines -= lines.filtered(self._l10n_pk_edi_is_global_discount)
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
            'totalSTWithheldAtSource': None,
            'totalExtraTax': None,
            'totalFEDPayable': None,
            'totalWithholdingIncomeTaxApplicable': None,
            'totalCVT': None,
            'totalDiscount': self._l10n_pk_edi_round_value(total_discount),
            'items': [
                self._get_l10n_pk_edi_line_details(line, tax_details_per_record.get(line, {}))
                for line in lines
            ],
        }
        if self._get_l10n_pk_edi_fbr_ref_number():
            json_payload['reason'] = self.l10n_pk_edi_cancel_reason
            json_payload['reasonRemarks'] = self.l10n_pk_edi_cancel_remarks
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

        '''
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
        '''

        results = self._l10n_pk_edi_generate(files_to_upload)
        messages_to_log = []
        for move_name in filename_move:
            move = filename_move[move_name]
            response = results[move_name]
            if response.get('errorMessage') or response.get('errors').get('$values'):
                error_response = []
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
                    "Error uploading the e-invoice file %(name)s.<br/>%(error)s",
                    name=move_name,
                    error=error_response,
                )
                move.sudo().message_post(body=Markup(error))
                move.l10n_pk_edi_header = error_response
                move.l10n_pk_edi_state = 'rejected'
                messages_to_log.append(error)
            else:
                message = (_("The e-invoice for %s was successfully sent to the FBR.", move_name))
                move.l10n_pk_edi_header = False
                move.l10n_pk_edi_state = 'sent'
                move.l10n_pk_edi_fbr_inv_ref = response.get('result')
                move.sudo().message_post(body=message)

    # -------------------------------------------------------------------------
    # API Methods
    # -------------------------------------------------------------------------

    def _l10n_pk_edi_connect_to_server(self, moves_json, use_timeout=False):
        proxy_address = self.company_id.sudo().l10n_pk_edi_proxy
        if not proxy_address:
            raise UserError(_("Please add a proxy server from configuration to test APIs"))
        results = {}
        for move_json in moves_json:
            try:
                results[move_json['name']] = requests.post(
                    DEFAULT_ENDPOINT,
                    json=move_json['json'],
                    headers={
                        'Authorization': f'Bearer {self.company_id.sudo().l10n_pk_edi_token}',
                        'Content-Type': 'application/json',
                    },
                    proxies={
                        'http': 'http://' + proxy_address,
                        'https': 'http://' + proxy_address,
                    },
                    # While using proxy server it may take longer than 25 sec
                    timeout=self.env['ir.config_parameter'].sudo().get_param(
                        'l10n_pk_edi.time_out',
                        use_timeout or DEFAULT_TIMEOUT
                    ),
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
        if not self.company_id.sudo().l10n_pk_edi_token:
            return {
                'statusCode': 0,
                'errorMessage': _(
                    "A token is still needs to be set or it's wrong for the E-invoice(Pakistan). "
                    "It needs to be added and verify in the Settings."
                )
            }
        return self._l10n_pk_edi_connect_to_server(moves_json)
