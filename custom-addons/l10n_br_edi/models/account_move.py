# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import models, fields, api, _
from odoo.addons.iap import InsufficientCreditError
from odoo.exceptions import UserError, ValidationError
from odoo.tools import street_split

FREIGHT_MODEL_SELECTION = [
    ("CIF", "Freight contracting on behalf of the Sender (CIF)"),
    ("FOB", "Contracting of freight on behalf of the recipient/sender (FOB)"),
    ("Thirdparty", "Contracting Freight on behalf of third parties"),
    ("SenderVehicle", "Own transport on behalf of the sender"),
    ("ReceiverVehicle", "Own transport on behalf of the recipient"),
    ("FreeShipping", "Free shipping"),
]

PAYMENT_METHOD_SELECTION = [
    ("01", "Money"),
    ("02", "Check"),
    ("03", "Credit Card"),
    ("04", "Debit Card"),
    ("05", "Store Credit"),
    ("10", "Food voucher"),
    ("11", "Meal Voucher"),
    ("12", "Gift certificate"),
    ("13", "Fuel Voucher"),
    ("14", "Duplicate Mercantil"),
    ("15", "Boleto Bancario"),
    ("16", "Bank Deposit"),
    ("17", "Instant Payment (PIX)"),
    ("18", "Bank transfer, Digital Wallet"),
    ("19", "Loyalty program, Cashback, Virtual Credit"),
    ("90", "No Payment"),
    ("99", "Others"),
]


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_br_edi_avatax_data = fields.Text(
        help="Brazil: technical field that remembers the last tax summary returned by Avatax.", copy=False
    )
    l10n_br_edi_is_needed = fields.Boolean(
        compute="_compute_l10n_br_edi_is_needed",
        help="Brazil: technical field to determine if this invoice is eligible to be e-invoiced.",
    )
    l10n_br_edi_transporter_id = fields.Many2one(
        "res.partner",
        "Transporter Brazil",
        help="Brazil: if you use a transport company, add its company contact here.",
    )
    l10n_br_edi_freight_model = fields.Selection(
        FREIGHT_MODEL_SELECTION,
        string="Freight Model",
        help="Brazil: used to determine the freight model used on this transaction.",
    )
    l10n_br_edi_payment_method = fields.Selection(
        PAYMENT_METHOD_SELECTION,
        string="Payment Method Brazil",
        help="Brazil: expected payment method to be used.",
    )
    l10n_br_access_key = fields.Char(
        "Access Key",
        copy=False,
        help="Brazil: access key associated with the electronic document. Can be used to get invoice information directly from the government.",
    )
    l10n_br_edi_error = fields.Text(
        "Brazil E-Invoice Error",
        copy=False,
        readonly=True,
        help="Brazil: error details for invoices in the 'error' state.",
    )
    l10n_br_last_edi_status = fields.Selection(
        [
            ("accepted", "Accepted"),
            ("error", "Error"),
            ("cancelled", "Cancelled"),
        ],
        string="Brazil E-Invoice Status",
        copy=False,
        tracking=True,
        readonly=True,
        help="Brazil: the state of the most recent e-invoicing attempt.",
    )
    l10n_br_edi_xml_attachment_file = fields.Binary(
        string="Brazil E-Invoice XML File",
        copy=False,
        attachment=True,
        help="Brazil: technical field holding the e-invoice XML data for security reasons.",
    )
    l10n_br_edi_xml_attachment_id = fields.Many2one(
        "ir.attachment",
        string="Brazil E-Invoice XML",
        compute=lambda self: self._compute_linked_attachment_id(
            "l10n_br_edi_xml_attachment_id", "l10n_br_edi_xml_attachment_file"
        ),
        depends=["l10n_br_edi_xml_attachment_file"],
        help="Brazil: the most recent e-invoice XML returned by Avalara.",
    )
    l10n_br_edi_last_correction_number = fields.Integer(
        "Brazil Correction Number",
        readonly=True,
        copy=False,
        help="Brazil: technical field that holds the latest correction that happened to this invoice",
    )

    def _l10n_br_call_avatax_taxes(self):
        """Override to store the retrieved Avatax data."""
        document_to_response = super()._l10n_br_call_avatax_taxes()

        for document, response in document_to_response.items():
            document.l10n_br_edi_avatax_data = json.dumps(
                {
                    "header": response.get("header"),
                    "lines": response.get("lines"),
                    "summary": response.get("summary"),
                }
            )

        return document_to_response

    @api.depends("l10n_br_last_edi_status", "country_code", "company_currency_id", "move_type", "fiscal_position_id")
    def _compute_l10n_br_edi_is_needed(self):
        for move in self:
            move.l10n_br_edi_is_needed = (
                not move.l10n_br_last_edi_status
                and move.country_code == "BR"
                and move.move_type in ("out_invoice", "out_refund")
                and move.fiscal_position_id.l10n_br_is_avatax
            )

    @api.depends("l10n_br_last_edi_status")
    def _compute_need_cancel_request(self):
        # EXTENDS 'account' to add dependencies
        super()._compute_need_cancel_request()

    def _need_cancel_request(self):
        # EXTENDS 'account'
        return super()._need_cancel_request() or self.l10n_br_last_edi_status == "accepted"

    def button_request_cancel(self):
        # EXTENDS 'account'
        if self._need_cancel_request() and self.l10n_br_last_edi_status == "accepted":
            return {
                "name": _("Fiscal Document Cancellation"),
                "type": "ir.actions.act_window",
                "view_type": "form",
                "view_mode": "form",
                "res_model": "l10n_br_edi.invoice.update",
                "target": "new",
                "context": {"default_move_id": self.id, "default_mode": "cancel"},
            }

        return super().button_request_cancel()

    def button_draft(self):
        # EXTENDS 'account'
        self.write(
            {
                "l10n_br_last_edi_status": False,
                "l10n_br_edi_error": False,
                "l10n_br_edi_avatax_data": False,
            }
        )
        return super().button_draft()

    def button_request_correction(self):
        return {
            "name": _("Fiscal Document Correction"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "l10n_br_edi.invoice.update",
            "target": "new",
            "context": {
                "default_move_id": self.id,
                "default_mode": "correct",
            },
        }

    def _l10n_br_iap_submit_invoice_goods(self, transaction):
        return self._l10n_br_iap_request("submit_invoice_goods", transaction)

    def _l10n_br_iap_cancel_invoice_goods(self, transaction):
        return self._l10n_br_iap_request("cancel_invoice_goods", transaction)

    def _l10n_br_iap_correct_invoice_goods(self, transaction):
        return self._l10n_br_iap_request("correct_invoice_goods", transaction)

    def _l10n_br_iap_cancel_range_goods(self, transaction, company):
        return self._l10n_br_iap_request("cancel_range_goods", transaction, company=company)

    def _l10n_br_edi_check_calculated_tax(self):
        if not self.l10n_br_edi_avatax_data:
            return [_('Tax has never been calculated on this invoice, please "Reset to Draft" and re-post.')]
        return []

    def _l10n_br_edi_get_xml_attachment_name(self):
        return f"{self.name}_edi.xml"

    def _l10n_br_edi_set_successful_status(self):
        """Can be overridden for invoices that are processed asynchronously."""
        self.l10n_br_last_edi_status = "accepted"

    def _l10n_br_edi_attachments_from_response(self, response):
        # Unset old ones because otherwise `_compute_linked_attachment_id()` will set the oldest
        # attachment, not this new one.
        self.invoice_pdf_report_id.res_field = False
        self.l10n_br_edi_xml_attachment_id.res_field = False

        # Creating the e-invoice PDF like this prevents the standard invoice PDF from being generated.
        invoice_pdf = self.env["ir.attachment"].create(
            {
                "res_model": "account.move",
                "res_id": self.id,
                "res_field": "invoice_pdf_report_file",
                "name": self._get_invoice_report_filename(),
                "datas": response["pdf"]["base64"],
            }
        )
        # make sure latest PDF shows to the right of the chatter
        invoice_pdf.register_as_main_attachment(force=True)

        invoice_xml = self.env["ir.attachment"].create(
            {
                "res_model": "account.move",
                "res_id": self.id,
                "res_field": "l10n_br_edi_xml_attachment_file",
                "name": self._l10n_br_edi_get_xml_attachment_name(),
                "datas": response["xml"]["base64"],
            }
        )
        self.invalidate_recordset(
            fnames=[
                "invoice_pdf_report_id",
                "invoice_pdf_report_file",
                "l10n_br_edi_xml_attachment_id",
                "l10n_br_edi_xml_attachment_file",
            ]
        )
        return invoice_pdf | invoice_xml

    def _l10n_br_edi_send(self):
        """Sends the e-invoice and returns an array of error strings."""
        for invoice in self:
            payload, validation_errors = invoice._l10n_br_prepare_invoice_payload()

            if validation_errors:
                return validation_errors
            else:
                response, api_error = self._l10n_br_submit_invoice(invoice, payload)
                if api_error:
                    invoice.l10n_br_last_edi_status = "error"
                    return [api_error]
                else:
                    invoice._l10n_br_edi_set_successful_status()
                    invoice.l10n_br_access_key = response["key"]

                    self.with_context(no_new_invoice=True).message_post(
                        body=_("E-invoice submitted successfully."),
                        attachment_ids=invoice._l10n_br_edi_attachments_from_response(response).ids,
                    )

                    # Now that the invoice is submitted and accepted we no longer need the saved tax computation data.
                    invoice.l10n_br_edi_avatax_data = False

    def _l10n_br_edi_vat_for_api(self, vat):
        # Typically users enter the VAT as e.g. "xx.xxx.xxx/xxxx-xx", but the API errors on non-digit characters
        return "".join(c for c in vat or "" if c.isdigit())

    def _l10n_br_edi_get_goods_values(self):
        """Returns the appropriate (finNFe, goal) tuple for the goods section in the header."""
        if self.debit_origin_id:
            return 2, "Complementary"
        elif self.move_type == "out_refund":
            return 4, "Return"
        else:
            return 1, "Normal"

    def _l10n_br_edi_get_invoice_refs(self):
        """For credit and debit notes this returns the appropriate reference to the original invoice. For tax
        calculation we send these references as documentCode, which are Odoo references (e.g. account.move_31).
        For EDI the government requires these references as refNFe instead. They should contain the access key
        assigned when the original invoice was e-invoiced. Returns a (dict, errors) tuple."""
        if origin := self._l10n_br_get_origin_invoice():
            if not origin.l10n_br_access_key:
                return {}, (
                    _(
                        "The originating invoice (%s) must have an access key before electronically invoicing %s. The access key can be set manually or by electronically invoicing %s.",
                        origin.display_name,
                        self.display_name,
                        origin.display_name,
                    )
                )

            return self._l10n_br_invoice_refs_for_code("refNFe", origin.l10n_br_access_key), None

        return {}, None

    def _l10n_br_edi_get_tax_data(self):
        """Due to Avalara bugs they're unable to resolve we have to change their tax calculation response before
        sending it back to them. This returns a tuple with what to include in the request ("lines" and "summary")
        and the header (separate because it shouldn't be included)."""
        # These return errors when null in /v3/invoices
        keys_to_remove_when_null = ("ruleId", "ruleCode")

        tax_calculation_response = json.loads(self.l10n_br_edi_avatax_data)
        for line in tax_calculation_response.get("lines", []):
            for detail in line.get("taxDetails", []):
                for key in keys_to_remove_when_null:
                    if key in detail and detail[key] is None:
                        del detail[key]

        return tax_calculation_response, tax_calculation_response.pop("header")

    def _l10n_br_edi_validate_partner(self, partner):
        required_fields = ("street", "street2", "zip", "vat")
        errors = []

        if not partner:
            return []

        for field in required_fields:
            if not partner[field]:
                errors.append(
                    _(
                        "%s on partner %s is required for e-invoicing",
                        partner._fields[field].string,
                        partner.display_name,
                    )
                )

        return errors

    def _l10n_br_prepare_payment_mode(self):
        payment_value = False
        if self.l10n_br_edi_payment_method != "90":  # if different from no payment
            payment_value = self.amount_total

        payment_mode = {
            "mode": self.l10n_br_edi_payment_method,
            "value": payment_value,
        }
        if self.l10n_br_edi_payment_method == "99":
            payment_mode["modeDescription"] = _("Other")

        card_methods = {"03", "04", "10", "11", "12", "13", "15", "17", "18"}
        if self.l10n_br_edi_payment_method in card_methods:
            payment_mode["cardTpIntegration"] = "2"

        return payment_mode

    def _l10n_br_prepare_invoice_payload(self):
        def deep_update(d, u):
            """Like {}.update but handles nested dicts recursively. Based on https://stackoverflow.com/a/3233356."""
            for k, v in u.items():
                if isinstance(v, dict):
                    d[k] = deep_update(d.get(k, {}), v)
                else:
                    d[k] = v
            return d

        def deep_clean(d):
            """Recursively removes keys with a falsy value in dicts. Based on https://stackoverflow.com/a/48152075."""
            cleaned_dict = {}
            for k, v in d.items():
                if isinstance(v, dict):
                    v = deep_clean(v)
                if v:
                    cleaned_dict[k] = v
            return cleaned_dict or None

        errors = []

        # Don't raise because it would break account.move.send's async batch mode.
        try:
            # The /transaction payload requires a superset of the /calculate payload we use for tax calculation.
            payload = self._l10n_br_get_calculate_payload()
        except (UserError, ValidationError) as e:
            payload = {}
            errors.append(str(e).replace("- ", ""))

        customer = self.partner_id
        customer_street_data = street_split(customer.street)
        company_partner = self.company_id.partner_id
        company_street_data = street_split(company_partner.street)

        transporter = self.l10n_br_edi_transporter_id
        is_invoice = self.move_type == "out_invoice"
        if self.l10n_br_edi_freight_model == "SenderVehicle":
            transporter = self.company_id.partner_id if is_invoice else customer
        elif self.l10n_br_edi_freight_model == "ReceiverVehicle":
            transporter = customer if is_invoice else self.company_id.partner_id

        transporter_street_data = street_split(transporter.street)

        errors.extend(self._l10n_br_edi_check_calculated_tax())
        errors.extend(self._l10n_br_edi_validate_partner(customer))
        errors.extend(self._l10n_br_edi_validate_partner(company_partner))
        errors.extend(self._l10n_br_edi_validate_partner(transporter))

        invoice_refs, error = self._l10n_br_edi_get_invoice_refs()
        if error:
            errors.append(error)

        goods_nfe, goods_goal = self._l10n_br_edi_get_goods_values()
        tax_data_to_include, tax_data_header = self._l10n_br_edi_get_tax_data()

        extra_payload = {
            "header": {
                "companyLocation": self._l10n_br_edi_vat_for_api(company_partner.vat),
                **invoice_refs,
                "locations": {
                    "entity": {
                        "name": customer.name,
                        "businessName": customer.name,
                        "federalTaxId": customer.vat,
                        "stateTaxId": customer.l10n_br_ie_code,
                        "address": {
                            "neighborhood": customer.street2,
                            "street": customer_street_data["street_name"],
                            "zipcode": customer.zip,
                            "cityName": customer.city,
                            "state": customer.state_id.name,
                            "number": customer_street_data["street_number"],
                            "phone": customer.phone,
                            "email": customer.email,
                        },
                    },
                    "establishment": {
                        "name": company_partner.name,
                        "businessName": company_partner.name,
                        "federalTaxId": company_partner.vat,
                        "cityTaxId": company_partner.l10n_br_im_code,
                        "stateTaxId": company_partner.l10n_br_ie_code,
                        "address": {
                            "neighborhood": company_partner.street2,
                            "cityName": company_partner.city,
                            "state": company_partner.state_id.name,
                            "countryCode": company_partner.country_id.l10n_br_edi_code,
                            "number": company_street_data["street_number"],
                        },
                    },
                    "transporter": {
                        "name": transporter.name,
                        "businessName": transporter.name,
                        "type": self._l10n_br_get_partner_type(transporter),
                        "federalTaxId": transporter.vat,
                        "cityTaxId": transporter.l10n_br_im_code,
                        "stateTaxId": transporter.l10n_br_ie_code,
                        "suframa": transporter.l10n_br_isuf_code,
                        "address": {
                            "street": transporter_street_data["street_name"],
                            "neighborhood": transporter.street2,
                            "zipcode": transporter.zip,
                            "state": transporter.state_id.name,
                            "countryCode": transporter.country_id.l10n_br_edi_code,
                            "number": transporter_street_data["street_number"],
                        },
                    },
                },
                "payment": {
                    "paymentInfo": {
                        "paymentMode": [
                            self._l10n_br_prepare_payment_mode(),
                        ],
                    },
                },
                "invoiceNumber": self.l10n_latam_document_number,
                "invoiceSerial": self.journal_id.l10n_br_invoice_serial,
                "goods": {
                    "model": self.l10n_latam_document_type_id.code,
                    "class": tax_data_header.get("goods", {}).get("class"),
                    "tplmp": "4",  # DANFe NFC-e
                    "goal": goods_goal,
                    "finNFe": goods_nfe,
                    "transport": {
                        "modFreight": self.l10n_br_edi_freight_model,
                    },
                },
            },
        }

        # extra_payload is cleaned before it's used to avoid e.g. "cityName": False or "number": "". These make
        # Avatax return various errors: e.g. "Falha na estrutura enviada". This is to avoid having lots of if
        # statements.
        deep_update(payload, deep_clean(extra_payload))

        # This adds the "lines" and "summary" dicts received during tax calculation.
        payload.update(tax_data_to_include)

        return payload, errors

    def _l10n_br_get_error_from_response(self, response):
        if error := response.get("error"):
            return f"Code {error['code']}: {error['message']}"

    def _l10n_br_submit_invoice(self, invoice, payload):
        try:
            response = invoice._l10n_br_iap_submit_invoice_goods(payload)
            return response, self._l10n_br_get_error_from_response(response)
        except (UserError, InsufficientCreditError) as e:
            # These exceptions can be thrown by iap_jsonrpc()
            return None, str(e)
