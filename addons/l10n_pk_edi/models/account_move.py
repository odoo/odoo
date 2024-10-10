# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import re
import requests

from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools import float_is_zero

DEFAULT_ENDPOINT = "https://gw.fbr.gov.pk/DigitalInvoicing/v1/PostInvoiceData_v1"
DEFAULT_TIMEOUT = 25
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_pk_edi_state = fields.Selection(
        string="E-Invoice(FBR) State",
        selection=[
            ('being_sent', 'Being Sent To FBR'),
            ('processing', 'Invoice is Processing'),
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
            move.show_reset_to_draft_button = not move.l10n_pk_edi_fbr_inv_ref and move.show_reset_to_draft_button

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
        for move in self:
            move.l10n_pk_edi_state = False
        return super().button_draft()

    def _post(self, soft=True):
        # EXTENDS 'account'
        corrupt_move_name = {}
        for move in self:
            if err_msg := move._l10n_pk_validate_move_for_fbr():
                corrupt_move_name[move.name] = ('\n').join(err_msg)
        if corrupt_move_name:
            error_msg = "\n\n".join(f"{name}:\n{err_msg}" for name, err_msg in corrupt_move_name.items())
            raise ValidationError(_(
                "Please configure following details to confirm Invoices. \n%s",
                error_msg
            ))
        for move in self:
            if (move.move_type in ['in_refund', 'out_refund']
                and (not move.l10n_pk_edi_cancel_reason or not move.l10n_pk_edi_cancel_remarks)
            ):
                corrupt_move_name[move.name] = 'error'
        if corrupt_move_name:
            error_msg = "\n".join(f"- {name}" for name, msg in corrupt_move_name.items())
            raise ValidationError(_(
                "To confirm credit note, set cancel reason and remarks at Electronic Invoicing tab in following invoices:\n%s",
                error_msg
            ))
        return super()._post(soft)

    def action_l10n_pk_edi_send(self):
        """
            Create a attachment and Send the invoice to the FBR.
        """
        self.ensure_one()
        attachment_vals = self._l10n_pk_edi_get_attachment_values()
        self.env['ir.attachment'].create(attachment_vals)
        self.invalidate_recordset(fnames=['l10n_pk_edi_attachment_id', 'l10n_pk_edi_attachment_file'])
        self.message_post(attachment_ids=self.l10n_pk_edi_attachment_id.ids)
        self._l10n_pk_edi_send({self: attachment_vals})
        self.is_move_sent = True

    # -------------------------------------------------------------------------
    # E-Invocing Methods
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
            if (sale_group_id := self.env['ir.model.data']._xmlid_to_res_model_res_id(
                f"account.{self.company_id.id}_{ref}"
            )[1])
        ])

    def _get_l10n_pk_withhold_groups(self):
        return self.env['account.chart.template'].with_company(self.company_id).ref('tax_group_pk_wt')

    def _l10n_pk_edi_get_default_enable(self):
        self.ensure_one()
        is_taxable = (
            self._get_l10n_pk_sales_groups()
            & self.line_ids.tax_ids.tax_group_id
        )
        return (
            self.state == 'posted'
            and self.company_id.account_fiscal_country_id.code == 'PK'
            and self.journal_id.type in ['sale', 'purchase']
            and self.l10n_pk_edi_state in (False, 'rejected')
            and is_taxable
        )

    def _l10n_pk_validate_move_for_fbr(self):
        error_messages = []
        for line in self.invoice_line_ids.filtered(
            lambda line: line.display_type == 'product'
            and not self._l10n_pk_is_global_discount(line)
        ):
            if line.discount < 0:
                error_messages.append(_("- Negative discount is not allowed, set in line %s", line.name))
            if not line.product_id.l10n_pk_edi_sale_type_id:
                error_messages.append(_("- Sale type is not defined for line %s", line.name))
            if not line.product_id.l10n_pk_edi_schedule_code_id:
                error_messages.append(_("- Schedule code is not defined for line %s", line.name))
            hs_code = self._l10n_pk_edi_extract_digits(line.product_id.hs_code)
            if not hs_code:
                error_messages.append(_("- HS code is not set in product line %s", line.name))
            elif not re.match("^[a-zA-Z0-9]{8}$", hs_code):
                error_messages.append(_(
                    "- The HS Code '%(hs_code)s' in product line %(product_line)s is invalid."
                    " Please ensure the code contains exactly 8 digits.",
                        hs_code=hs_code,
                        product_line=line.product_id.name or line.name
                    )
                )
        return error_messages

    def _l10n_pk_validate_seller(self, partner):
        self.ensure_one()
        messages = []
        if not re.match("^.{3,100}$", partner.street or ""):
            messages.append(_("- Street required min 3 and max 100 characters"))
        if not re.match("^.{3,100}$", partner.street2 or ""):
            messages.append(_("- Street2 should be min 3 and max 100 characters"))
        if not re.match("^.{3,50}$", partner.state_id.name or ""):
            messages.append(_("- State required min 3 and max 50 characters"))
        if messages:
            error_msg = '\n'.join(map(str, messages))
            raise RedirectWarning(
                _(
                    "Please enter required details for %(name)s \n%(message)s",
                    name=partner.display_name, message=error_msg
                ),
                partner._get_records_action(name=_("Check Partner")),
                _('Go to Configuration')
            )

    def _l10n_pk_validate_buyer(self, partner):
        self.ensure_one()
        if not re.match("^.{3,50}$", partner.state_id.name or ""):
            raise RedirectWarning(
                _(
                    "Please enter required details for %s \n- State required min 3 and max 50 characters",
                    partner.display_name
                ),
                partner._get_records_action(name=_("Check Partner")),
                _('Go to Configuration')
            )

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

    @api.model
    def _get_l10n_pk_edi_partner_address(self, partner):
        zip_digits = self._l10n_pk_edi_extract_digits(partner.zip)
        address_parts = [
            partner.street or "",
            partner.street2 or "",
            partner.city or "",
            partner.state_id.name or "",
            f"Pin: {zip_digits}" if zip_digits else ""
        ]
        partner_address = ", ".join(part for part in address_parts if part)
        return partner_address

    @api.model
    def _get_l10n_pk_edi_partner_vat(self):
        company = self.company_id
        if not company.vat or not re.match("^[0-9]{7}$", company.vat):
            raise RedirectWarning(
                _(
                    "The NTN number is invalid or has not been configured for %s. "
                    "It must be 7 digit number.",
                    company.name
                ),
                company._get_records_action(name=_("Check Company")),
                _('Go to Company')
            )
        return company.vat

    @api.model
    def _get_l10n_pk_edi_partner_pos_id(self):
        company = self.company_id
        if not company.l10n_pk_edi_pos_key:
            raise RedirectWarning(
                _("Please configure PoS ID for %s in Pakistan Localisation.", company.partner_id.name),
                self.env.ref('account.action_account_config').id,
                _('Go to Configuration')
            )
        return company.l10n_pk_edi_pos_key

    def _get_l10n_pk_edi_line_details(self, index, line, line_tax_details):
        move_id = line.move_id
        product_id = line.product_id
        sale_value = line.balance * (1 if move_id.is_outbound() else -1)
        quantity = line.quantity or 0.0
        prd_desc = product_id.display_name or line.name
        tax_lines = self._get_l10n_pk_tax_details_by_line(line_tax_details.get('tax_details', {}))
        sales_tax_total, non_sales_tax_total = self._get_l10n_pk_total_tax_values(tax_lines)
        tax_withholdings = tax_lines.get(self._get_l10n_pk_withhold_groups()[0], {})
        full_discount_or_zero_quantity = line.discount == 100.00 or float_is_zero(quantity, 3)
        discount_percentage = line.discount / 100
        if full_discount_or_zero_quantity:
            unit_price_in_pkr = line.currency_id._convert(
                line.price_unit,
                line.company_currency_id,
                line.company_id,
                line.date or fields.Date.context_today(self)
            )
        else:
            unit_price_in_pkr = (sale_value / (1 - discount_percentage)) / quantity
        line_discount = (unit_price_in_pkr * quantity) * discount_percentage
        line_json = {
            "hsCode": self._l10n_pk_edi_extract_digits(product_id.hs_code),
            "productCode": product_id.code,
            "productDescription": prd_desc.replace("\n", ""),
            "rate": self._l10n_pk_round_value(line.price_unit),
            "uoM": line.product_uom_id.l10n_pk_code,
            "quantity": self._l10n_pk_round_value(quantity),
            "valueSalesExcludingST": self._l10n_pk_round_value(sale_value + line_discount),
            "salesTaxApplicable": self._l10n_pk_round_value(sales_tax_total),
            "retailPrice": self._l10n_pk_round_value(line.price_unit),
            "salesTaxWithheldAtSource": 0.0,
            "extraTax": self._l10n_pk_round_value(non_sales_tax_total or 0.0),
            "furtherTax": 0.0,
            "sroScheduleNo": None,
            "fedPayable": 0.0,
            "cvt": 0.0,
            "withholdingIncomeTaxApplicable": self._l10n_pk_round_value(tax_withholdings.get('amount', 0.0)),
            "whiT_1": 0.0,
            "whiT_2": None,
            "whiT_Section_1": None,
            "whiT_Section_2": "0.0",
            "totalValues": self._l10n_pk_round_value(sale_value + sales_tax_total),
            "discount": self._l10n_pk_round_value(line_discount),
            "sroItemSerialNo": (
                product_id.l10n_pk_edi_schedule_code_id.schedule_code[-3:]
                if product_id.l10n_pk_edi_schedule_code_id else False
            ),
            "stWhAsWhAgent": 0,
        }
        line_json[
            "saleType" if move_id.is_sale_document() else "purchaseType"
        ] = product_id.l10n_pk_edi_sale_type_id.sale_type
        if reference_number := self._get_l10n_pk_edi_fbr_ref_number():
            line_json["invoiceRefNo"] = reference_number
        return line_json

    def _l10n_pk_edi_generate_invoice_json(self):
        def _get_buyer_seller():
            if self.is_sale_document():
                return self.partner_id, self.company_id.partner_id
            else:  # purchase_document
                return self.company_id, self.partner_id
        tax_details = self._prepare_invoice_aggregated_taxes()
        tax_details_per_record = tax_details.get("tax_details_per_record")
        lines = self.invoice_line_ids.filtered(lambda line: line.display_type not in (
            'line_note', 'line_section', 'rounding'
        ))
        global_discount_line = lines.filtered(self._l10n_pk_is_global_discount)
        lines -= global_discount_line
        # Calculate the total discount as the sum of the global discount and the line discounts
        total_discount = (
            sum(line.balance for line in global_discount_line) * (1 if self.is_inbound() else -1)
        ) + sum((line.price_unit * line.quantity) * (line.discount / 100) for line in lines)
        # Total Sale Value (Excluding Discount and Tax Amount)
        total_sale_value = sum(line.price_unit * line.quantity for line in lines)
        # Validate Buyer and Seller
        buyer, seller = _get_buyer_seller()
        self._l10n_pk_validate_buyer(buyer)
        self._l10n_pk_validate_seller(seller)
        json_payload = {
            "bposid": self._get_l10n_pk_edi_partner_pos_id(),
            "invoiceType": self._get_l10n_pk_edi_invoice_type(),
            "invoiceDate": self.format_timestamp(self.invoice_date),
            "sellerNTNCNIC": self._get_l10n_pk_edi_partner_vat(),
            "sellerProvince": seller.state_id.name,
            "sellerBusinessName": seller.name,
            "businessDestinationAddress": self._get_l10n_pk_edi_partner_address(seller),
            "buyerNTNCNIC": buyer.vat or "",
            "buyerBusinessName": buyer.name or "",
            "buyerProvince": buyer.state_id.name,
            "saleType": "T1000017",
            "salesValue": self._l10n_pk_round_value(total_sale_value + tax_details.get("tax_amount") - total_discount),
            "totalSalesTaxApplicable": self._l10n_pk_round_value(tax_details.get("tax_amount")),
            "totalRetailPrice": self._l10n_pk_round_value(sum(line.price_unit for line in lines)),
            "totalSTWithheldAtSource": None,
            "totalExtraTax": None,
            "totalFEDPayable": None,
            "totalWithholdingIncomeTaxApplicable": None,
            "totalCVT": None,
            "totalDiscount": self._l10n_pk_round_value(total_discount),
            "items": [
                self._get_l10n_pk_edi_line_details(index, line, tax_details_per_record.get(line, {}))
                for index, line in enumerate(lines, start=1)
            ],
        }
        if self._get_l10n_pk_edi_fbr_ref_number():
            json_payload["reason"] = self.l10n_pk_edi_cancel_reason
            json_payload["reasonRemarks"] = self.l10n_pk_edi_cancel_remarks
        return json_payload

    def _get_l10n_pk_total_tax_values(self, tax_lines):
        sales_tax_total = 0.0
        non_sales_tax_total = 0.0
        sale_group_ids = (
            self._get_l10n_pk_sales_groups()
            + self._get_l10n_pk_withhold_groups()
        ).ids
        for tax_group_id in tax_lines:
            if tax_group_id in sale_group_ids:
                sales_tax_total += tax_lines[tax_group_id]['amount']
            else:
                non_sales_tax_total += tax_lines[tax_group_id]['amount']
        return sales_tax_total, non_sales_tax_total

    def _get_l10n_pk_tax_details_by_line(self, tax_details):
        l10n_pk_tax_details = {}
        for tax_detail in tax_details.values():
            line_code = tax_detail["tax"].tax_group_id.id
            l10n_pk_tax_detail = l10n_pk_tax_details.get(line_code, {})
            l10n_pk_tax_detail.update(dict.fromkeys(("rate", "amount", "amount_currency"), 0.0))
            l10n_pk_tax_detail["rate"] += tax_detail["tax"].amount
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
                "$id": "1",
                "version": "1.0",
                "statusCode": 200,
                "errorMessage": "",
                "result": "900005CLNP5914173522",
                "timestamp": "2023-12-20T16:59:15",
                "errors": {
                    "$id": "2",
                    "$values": []
                }
            }

            Example response with error messages and details in the `errorMessage`
            field and the `errors["$values"]` array.
            {
                "$id": "1",
                "version": "1.0",
                "statusCode": 200,
                "errorMessage": "Invalid BPOSID Not Found!",
                "result": "",
                "timestamp": "2024-08-30T13:35:42",
                "errors": {
                    "$id": "2",
                    "$values": [
                        "The SellerNTNCNIC field is required.",
                        "The SellerProvince field is required."
                    ]
                }
            }
        """
        results = self._l10n_pk_edi_generate(files_to_upload)
        messages_to_log = []
        for move_name in filename_move:
            move = filename_move[move_name]
            response = results[move_name]
            if response.get("errorMessage") or response.get("errors").get('$values'):
                error_response = []
                if response.get("errorMessage"):
                    error_response.extend(response.get("errorMessage").split(','))
                if response.get("errors") and response.get("errors").get('$values'):
                    error_response.extend(response.get("errors").get('$values'))
                error_response = "<br/>".join(f"- {err}" for err in error_response)
                error_response = "Error uploading the e-invoice as mention below<br/>" + error_response
                error = _(
                    "Error uploading the e-invoice file %(name)s.<br/>%(error)s",
                    name=move_name, error=error_response
                )
                move.sudo().message_post(body=error)
                move.l10n_pk_edi_header = error_response
                move.l10n_pk_edi_state = 'rejected'
                messages_to_log.append(error)
            else:
                message = (_("The e-invoice for %s was successfully sent to the FBR.", move_name))
                move.l10n_pk_edi_header = False
                move.l10n_pk_edi_state = 'sent'
                move.l10n_pk_edi_fbr_inv_ref = response.get("result")
                move.sudo().message_post(body=message)

    # -------------------------------------------------------------------------
    # API Methods
    # -------------------------------------------------------------------------

    @api.model
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
                        'Authorization': f"Bearer {self.company_id.sudo().l10n_pk_edi_token}",
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

    @api.model
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
