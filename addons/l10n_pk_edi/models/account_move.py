# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import re
import requests

from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

DEFAULT_API_KEY = "1298b5eb-b252-3d97-8622-a4a69d5bf818"
DEFAULT_ENDPOINT = "https://gw.fbr.gov.pk/imsp/v1/api/Live/PostData"
DEFAULT_TIMEOUT = 25


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_pk_edi_state = fields.Selection(
        string="E-Invoice(FBR) State",
        selection=[
            ('being_sent', 'Being Sent To FBR'),
            ('error', 'Error while sending to FBR'),
            ('sent', 'Invoice Filed to FBR'),
            ('rejected', 'Invoice Rejected'),
        ],
        copy=False, tracking=True, readonly=True,
    )
    l10n_pk_edi_header = fields.Html(
        help='User description of the current state, with hints to make the flow progress',
        readonly=True,
        copy=False,
    )
    l10n_pk_edi_show_send_to_fbr = fields.Boolean(
        compute="_compute_l10n_pk_edi_show_send_to_fbr",
        string="Show Send to FBR button on view?"
    )
    l10n_pk_edi_fbr_inv_ref = fields.Char(copy=False, string="FBR Refrence Number")
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
    l10n_pk_edi_cancel_reason = fields.Selection(selection=[
        ("1", "Duplicate"),
        ("2", "Data Entry Mistake"),
        ("3", "Order Cancelled"),
        ("4", "Others"),
    ], string="Cancel reason", copy=False)
    l10n_pk_edi_cancel_remarks = fields.Char("Cancel remarks", copy=False)

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    @api.depends('l10n_pk_edi_fbr_inv_ref')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_pk_edi_show_send_to_fbr:
                move.show_reset_to_draft_button = (
                    not move.l10n_pk_edi_fbr_inv_ref
                    and move.show_reset_to_draft_button
                )

    @api.depends('state')
    def _compute_l10n_pk_edi_show_send_to_fbr(self):
        for move in self:
            move.l10n_pk_edi_show_send_to_fbr = self._l10n_pk_edi_eligible_for_fbr()

    # -------------------------------------------------------------------------
    # Business actions
    # -------------------------------------------------------------------------

    def button_draft(self):
        # EXTENDS 'account'
        for move in self:
            move.l10n_pk_edi_state = False
        return super().button_draft()

    def _post(self, soft=True):
        # EXTENDS 'account'
        if self.company_id.account_fiscal_country_id.code != "PK":
            return super()._post(soft)
        if self._l10n_pk_edi_eligible_for_fbr() and (error := self._l10n_pk_validate_moves()):
            raise ValidationError(_(
                "%(title)s\n%(msg)s",
                title=error['title'], msg=error['msg']
            ))
        return super()._post(soft)

    def action_l10n_pk_edi_send(self):
        """
            Create a attachment and Send the invoice to the FBR.
        """
        self.ensure_one()
        attachment_vals = self._l10n_pk_edi_get_attachment_values()
        self.env['ir.attachment'].create(attachment_vals)
        self.invalidate_recordset(fnames=[
            'l10n_pk_edi_attachment_id',
            'l10n_pk_edi_attachment_file'
        ])
        self.message_post(attachment_ids=self.l10n_pk_edi_attachment_id.ids)
        self._l10n_pk_edi_send({self: attachment_vals})
        self.is_move_sent = True

    # -------------------------------------------------------------------------
    # E-Invocing(FBR) Eligibility
    # -------------------------------------------------------------------------

    def _get_l10n_pk_sales_groups(self):
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
            if (sale_group_id := self.env['ir.model.data']._xmlid_to_res_id(
                f"account.{self.company_id.id}_{ref}"
            ))
        ])

    def _get_l10n_pk_withhold_groups(self):
        self.ensure_one()
        return self.env['account.chart.template'].with_company(self.company_id).ref('tax_group_pk_wt')

    def _l10n_pk_edi_eligible_for_fbr(self):
        self.ensure_one()
        # Check whether the invoice is eligible for E-Invocing(FBR) or not.
        return (
            self.company_id.account_fiscal_country_id.code == 'PK'
            and self.is_sale_document
            and self.pos_order_ids
            and (  # is taxable
                self._get_l10n_pk_sales_groups()
                & self.line_ids.tax_ids.tax_group_id
            )
        )

    def _l10n_pk_edi_get_default_enable(self):
        self.ensure_one()
        return (
            self.state == 'posted'
            and self.l10n_pk_edi_state != 'sent'
            and self._l10n_pk_edi_eligible_for_fbr()
        )

    # -------------------------------------------------------------------------
    # E-Invocing Methods
    # -------------------------------------------------------------------------

    def _l10n_pk_validate_moves(self):
        corrupt_moves = {}
        move_ids = self.filtered(lambda m: m.is_sale_document())
        for move in move_ids:
            if err_msg := move._l10n_pk_validate_move_lines():
                corrupt_moves[move.name] = ('\n').join(err_msg)
            elif move.move_type == 'out_refund' and (
                not move.l10n_pk_edi_cancel_reason
                or not move.l10n_pk_edi_cancel_remarks
            ):
                corrupt_moves[move.name] = _('Set cancel reason and remarks')
        if corrupt_moves:
            error_msg = "\n\n".join(f"{name}:\n{msg}" for name, msg in corrupt_moves.items())
            return {
                "title": _("Please address the following issues before confirming Invoices:"),
                "msg": error_msg,
            }
        return False

    def _l10n_pk_validate_move_lines(self):
        error_messages = []
        for line in self.invoice_line_ids.filtered(
            lambda line: line.display_type == 'product'
            and not self._l10n_pk_is_global_discount(line)
        ):
            if line.discount < 0:
                error_messages.append(_("- Negative discount is not allowed, set in line %s", line.name))
            pct_code = self._l10n_pk_edi_extract_digits(line.product_id.l10n_pk_edi_pct_code)
            if not pct_code:
                error_messages.append(_("- PCT code is not set in product line %s", line.name))
            elif not re.match("^[a-zA-Z0-9]{8}$", pct_code):
                error_messages.append(_(
                    "- The PCT Code '%(pct_code)s' in product line %(product_line)s is invalid."
                    " Please ensure the code contains exactly 8 digits.",
                        pct_code=pct_code,
                        product_line=line.product_id.name or line.name
                    )
                )
        return error_messages

    def _get_l10n_pk_edi_payment_mode(self):
        """
            Payment Mode for invocie according to FBR:
            1. Cash
            2. Card
            3. Gift Voucher
            4. Loyalty Card
            5. Mixed
            6. Cheque
        """
        payments = self.pos_order_ids.mapped('payment_ids')
        if len(payments) > 1:
            # If multiple payment modes are used,
            # Return 5 to represent 'Mixed' as the payment mode.
            return 5
        return {
            'cash': 1,
            'card': 2,
        }.get(payments[0].payment_method_id.type)

    def format_timestamp(self, d):
        return datetime(d.year, d.month, d.day).isoformat(timespec='milliseconds') + 'Z'

    @api.model
    def _l10n_pk_round_value(self, amount, precision_digits=2):
        """
            This method is call for rounding.
            If anything is wrong with rounding then we quick fix in method
        """
        return round(amount, precision_digits) or 0.0  # avoid -0.0

    def _l10n_pk_edi_extract_digits(self, string):
        if not string:
            return string
        return re.sub('[^0-9]', '', string)

    def _l10n_pk_is_global_discount(self, line):
        return not line.tax_ids and line.price_subtotal < 0

    def _get_l10n_pk_edi_invoice_type(self):
        # The default value is set to 1, indicating a new invoice ('out_invoice').
        return {
            'out_refund': 3,
        }.get(self.move_type, 1)

    def _get_l10n_pk_edi_fbr_ref_number(self):
        if self.move_type == 'out_refund':
            return self.reversed_entry_id.l10n_pk_edi_fbr_inv_ref
        return False

    @api.model
    def _get_l10n_pk_edi_partner_pos_id(self):
        pos_config_id = self.pos_order_ids.config_id
        if not pos_config_id.l10n_pk_edi_pos_key:
            raise ValidationError(_(
                "Please configure the PoS key for %s to enable e-invoicing.",
                pos_config_id.name
            ))
        return pos_config_id.l10n_pk_edi_pos_key

    def _get_l10n_pk_edi_line_details(self, index, line, line_tax_details):
        product_id = line.product_id
        quantity = line.quantity or 0.0
        sale_value = line.balance * (1 if line.move_id.is_outbound() else -1)
        prd_desc = product_id.display_name or line.name
        tax_lines = self._get_l10n_pk_tax_details_by_line(
            line_tax_details.get('tax_details', {})
        )
        sales_tax_total, withhold_tax_total, non_sales_tax_total = (
            self._get_l10n_pk_total_tax_values(tax_lines)
        )
        line_discount = (line.price_unit * quantity) * (line.discount / 100)
        line_json = {
            "ItemCode": product_id.code,
            "ItemName": prd_desc.replace("\n", ""),
            "PCTCode": self._l10n_pk_edi_extract_digits(product_id.l10n_pk_edi_pct_code),
            "Quantity": self._l10n_pk_round_value(quantity),
            "TaxRate": 6,
            "SaleValue": self._l10n_pk_round_value(sale_value + line_discount),
            "Discount": self._l10n_pk_round_value(line_discount),
            "FurtherTax": self._l10n_pk_round_value(
                withhold_tax_total + non_sales_tax_total
            ),
            "TaxCharged": self._l10n_pk_round_value(sales_tax_total),
            "TotalAmount": self._l10n_pk_round_value(
                sale_value + sales_tax_total + withhold_tax_total + non_sales_tax_total
            ),
            "InvoiceType": 1,
        }
        if reference_number := self._get_l10n_pk_edi_fbr_ref_number():
            line_json["RefUSIN"] = reference_number
        return line_json

    def _l10n_pk_edi_generate_invoice_json(self):
        buyer = self.partner_id
        lines = self.invoice_line_ids.filtered(lambda line: line.display_type not in (
            'line_note', 'line_section', 'rounding'
        ))
        global_discount_line = lines.filtered(self._l10n_pk_is_global_discount)
        lines -= global_discount_line
        tax_details = self._prepare_invoice_aggregated_taxes()
        tax_details_per_record = tax_details.get("tax_details_per_record")
        total_quantity = sum(line.quantity for line in lines)
        # Calculate the total discount as the sum of the global discount and the line discounts
        total_discount = (
            sum(line.balance for line in global_discount_line) * (1 if self.is_inbound() else -1)
        ) + sum((line.price_unit * line.quantity) * (line.discount / 100) for line in lines)
        # Total Sale Value (Excluding Discount and Tax Amount)
        total_sale_value = sum(line.price_unit * line.quantity for line in lines)

        json_payload = {
            "InvoiceNumber": "",
            "POSID": self._get_l10n_pk_edi_partner_pos_id(),
            "USIN": self.name.replace('/', '_'),
            "DateTime": self.format_timestamp(self.invoice_date),
            "BuyerNTN": buyer.vat or "",
            "BuyerCNIC": None,
            "BuyerName": buyer.name or "",
            "BuyerPhoneNumber": None,
            "TotalBillAmount": self._l10n_pk_round_value(
                tax_details.get("base_amount") + tax_details.get("tax_amount")
            ),
            "TotalQuantity": total_quantity,
            "TotalSaleValue": self._l10n_pk_round_value(total_sale_value),
            "TotalTaxCharged": self._l10n_pk_round_value(tax_details.get("tax_amount")),
            "Discount": self._l10n_pk_round_value(total_discount),
            "FurtherTax": 0.00,
            "PaymentMode": self._get_l10n_pk_edi_payment_mode(),
            "RefUSIN": None,
            "InvoiceType": self._get_l10n_pk_edi_invoice_type(),
            "Items": [
                self._get_l10n_pk_edi_line_details(index, line, tax_details_per_record.get(line, {}))
                for index, line in enumerate(lines, start=1)
            ],
        }
        return json_payload

    def _get_l10n_pk_total_tax_values(self, tax_lines):
        sales_tax_total = 0.0
        withhold_tax_total = 0.0
        non_sales_tax_total = 0.0
        sale_group_ids = self._get_l10n_pk_sales_groups().ids
        withhold_group_ids = self._get_l10n_pk_withhold_groups().ids
        for tax_group_id in tax_lines:
            if tax_group_id in sale_group_ids:
                sales_tax_total += tax_lines[tax_group_id]['amount']
            elif tax_group_id in withhold_group_ids:
                withhold_tax_total += tax_lines[tax_group_id]['amount']
            else:
                non_sales_tax_total += tax_lines[tax_group_id]['amount']
        return sales_tax_total, withhold_tax_total, non_sales_tax_total

    def _get_l10n_pk_tax_details_by_line(self, tax_details):
        l10n_pk_tax_details = {}
        for tax_detail in tax_details.values():
            tax = tax_detail["taxes_data"][0].get("tax")
            line_code = tax.tax_group_id.id
            l10n_pk_tax_detail = l10n_pk_tax_details.get(line_code, {})
            l10n_pk_tax_detail.update(dict.fromkeys(("rate", "amount", "amount_currency"), 0.0))
            l10n_pk_tax_detail["rate"] += tax.amount
            l10n_pk_tax_detail["amount"] += tax_detail["tax_amount"]
            l10n_pk_tax_detail["amount_currency"] += tax_detail["tax_amount_currency"]
            l10n_pk_tax_details[line_code] = l10n_pk_tax_detail
        return l10n_pk_tax_details

    def _l10n_pk_edi_get_attachment_values(self):
        self.ensure_one()
        return {
            'name': f'{self.name.replace("/", "_")}_fbr_content.json',
            'type': 'binary',
            'mimetype': 'application/json',
            'description': _('EDI e-move: %s', self.move_type),
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
                "FBRInvoiceNumber": 11000120181112000369,
                "Code": "100",
                "Response": "Invoice received successfully",
                "Errors": null
            }

            Example response with error messages and details in the `Response` and `Errors`
            field and the `errors["$values"]` array.
            {
                "FBRInvoiceNumber": "Not Available",
                "Code": "104",
                "Response": "You are not authorized to use this service.",
                "Errors": null
            }
        """
        results = self._l10n_pk_edi_generate(files_to_upload)
        messages_to_log = []
        for move_name, move in filename_move.items():
            response = results[move_name]
            if response.get("Code") != "100":
                error_response = []
                if response.get("Response"):
                    error_response.extend(response.get("Response").split(','))
                if response.get("Errors"):
                    error_response.extend(response.get("Errors"))
                error_response = "<br/>".join(f"- {err}" for err in error_response)
                error_response = "Error uploading the e-invoice as mention below<br/>" + error_response
                error = _(
                    "Error uploading the e-invoice file %(name)s.<br/>%(error)s",
                    name=move_name, error=error_response
                )
                move.sudo().message_post(body=error)
                move.l10n_pk_edi_header = error_response
                move.l10n_pk_edi_state = 'error' if response.get("Code") == 104 else 'rejected'
                messages_to_log.append(error)
            else:
                message = (_("The e-invoice for %s was successfully sent to the FBR.", move_name))
                move.l10n_pk_edi_header = False
                move.l10n_pk_edi_state = 'sent'
                move.l10n_pk_edi_fbr_inv_ref = response.get("FBRInvoiceNumber")
                move.sudo().message_post(body=message)

    # -------------------------------------------------------------------------
    # API Methods
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_pk_edi_connect_to_server(self, moves_json, use_timeout=False):
        proxy_address = self.company_id.sudo().l10n_pk_edi_proxy
        if not proxy_address:
            raise ValidationError(_("Please add a proxy server from configuration to test APIs"))
        results = {}
        for move_json in moves_json:
            try:
                results[move_json['name']] = requests.post(
                    DEFAULT_ENDPOINT,
                    json=move_json['json'],
                    headers={
                        'Authorization': f"Bearer {DEFAULT_API_KEY}",
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
                    'Code': 104,
                    'Response': _("Unable to connect to the online E-invoice(Pakistan) service. "
                        "The web service may be temporary down. Please try again in a moment."
                    )
                }
        return results

    @api.model
    def _l10n_pk_edi_generate(self, moves_json):
        if not DEFAULT_API_KEY:
            return {
                'Code': 104,
                'Response': _(
                    "A token is still needs to be set or it's wrong for the E-invoice(Pakistan). "
                    "It needs to be added and verify in the Settings."
                )
            }
        return self._l10n_pk_edi_connect_to_server(moves_json)
