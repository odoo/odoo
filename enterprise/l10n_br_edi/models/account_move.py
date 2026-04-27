# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging

from lxml import etree
from markupsafe import Markup
from stdnum.br.cnpj import format as format_cnpj
from stdnum.br.cpf import format as format_cpf

from odoo import models, fields, api, _, Command
from odoo.addons.iap import InsufficientCreditError
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html2plaintext
from odoo.tools.xml_utils import find_xml_value

_logger = logging.getLogger(__name__)

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
            ("pending", "Pending"),
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
    l10n_br_nfse_number = fields.Char(
        "NFS-e Number",
        help="Brazil: After an NFS-e invoice is issued and confirmed by the municipality, an NFS-e number is provided.",
    )
    l10n_br_nfse_verification = fields.Char(
        "NFS-e Verification Code",
        help="Brazil: After an NFS-e invoice is issued and confirmed by the municipality, a unique code is provided for online verification of its authenticity.",
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

    @api.depends("l10n_br_last_edi_status")
    def _compute_show_reset_to_draft_button(self):
        """Override. Don't show resetting to draft when the invoice is pending. It's already been sent and the user
        should wait for the final result of that."""
        super()._compute_show_reset_to_draft_button()
        self.filtered(lambda move: move.l10n_br_last_edi_status == "pending").show_reset_to_draft_button = False

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

    def button_cancel(self):
        # EXTENDS 'account'
        res = super().button_cancel()
        self.l10n_br_last_edi_status = "cancelled"
        return res

    def _get_fields_to_detach(self):
        # EXTENDS account
        fields_list = super()._get_fields_to_detach()
        fields_list.append('l10n_br_edi_xml_attachment_file')
        return fields_list

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

    def button_l10n_br_edi_get_service_invoice(self):
        """Checks if the invoice received final approval from the government."""
        if self.l10n_br_last_edi_status != "pending":
            return

        response = self._l10n_br_iap_request(
            "get_invoice_services",
            {
                "serie": self.journal_id.l10n_br_invoice_serial,
                "number": self.l10n_latam_document_number,
            },
        )
        if error := self._l10n_br_get_error_from_response(response):
            self.l10n_br_last_edi_status = "error"
            self.l10n_br_edi_error = error
            self.with_context(no_new_invoice=True).message_post(body=_("E-invoice was not accepted:\n%s", error))
            return

        status = response.get("status", {})
        response_code = status.get("code")
        attachments = self.env["ir.attachment"]
        subtype_xmlid = None
        if response_code == "105":
            message = _("E-invoice is pending: %s", status.get("desc"))
        elif response_code in ("100", "200"):
            self.l10n_br_last_edi_status = "accepted"
            self.l10n_br_nfse_number = status.get("nfseNumber")
            self.l10n_br_nfse_verification = status.get("nfseVerifyCode")

            message = (
                Markup(
                    "%s"
                    "<ul>"
                    "  <li>%s</li>"
                    "  <li>%s</li>"
                    "  <li>%s</li>"
                    "</ul>"
                )
                % (
                    _("E-invoice accepted:"),
                    _("Status: %s", status.get("desc")),
                    _("NFS-e number: %s", self.l10n_br_nfse_number),
                    _("NFS-e verify code: %s", self.l10n_br_nfse_verification),
                )
            )
            attachments = self._l10n_br_edi_attachments_from_response(response)
            subtype_xmlid = "mail.mt_comment"  # send to all followers
        else:
            message = _("Unknown E-invoice status code %(code)s: %(description)s", code=response_code, description=status.get("desc"))

        self.with_context(no_new_invoice=True).message_post(
            body=message, attachment_ids=attachments.ids, subtype_xmlid=subtype_xmlid
        )

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
        self._message_set_main_attachment_id(invoice_pdf, force=True, filter_xml=False)

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
                    invoice.l10n_br_last_edi_status = "pending" if invoice.l10n_br_is_service_transaction else "accepted"
                    invoice.l10n_br_access_key = response["key"]

                    invoice.with_context(no_new_invoice=True).message_post(
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
                        "The originating invoice (%(origin_invoice)s) must have an access key before electronically invoicing %(current_invoice)s. The access key can be set manually or by electronically invoicing %(origin_invoice)s.",
                        origin_invoice=origin.display_name,
                        current_invoice=self.display_name,
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
        if not partner:
            return []

        errors = []
        requires_minimal_info = (
            self.l10n_br_is_service_transaction and
            partner.l10n_br_tax_regime == "individual" and
            partner.l10n_br_activity_sector == "finalConsumer" and
            partner.l10n_latam_identification_type_id == self.env.ref("l10n_br.cpf")
        )
        required_fields = ("zip",) if requires_minimal_info else ("street", "street2", "zip", "vat")

        for field in required_fields:
            if not partner[field]:
                errors.append(
                    _(
                        "%(field)s on partner %(partner)s is required for e-invoicing",
                        field=partner._fields[field].string,
                        partner=partner.display_name,
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

    def _l10n_br_log_informative_taxes(self, payload):
        skip_icmsDeson = any(
            td['taxImpact']['accounting'] == 'none' and td['taxType'] == 'icmsDeson'
            for line in payload.get("lines", [])
            for td in line.get("taxDetails", [])
        )

        informative_taxes = []
        taxes_summary = payload.get("summary", {}).get("taxImpactHighlights", {})
        for tax_type, taxes in taxes_summary.items():
            if tax_type == 'informative':
                informative_taxes += taxes
            elif skip_icmsDeson:
                informative_taxes += [tax for tax in taxes if tax['taxType'] == 'icmsDeson']
        # Informative taxes look like: [{"taxType": "aproxtribCity", "tax": 7.8, "subtotalTaxable": 200}, ...]
        # Transform to:
        # - taxType: aproxtribCity, tax: 7.8, subtotalTaxable: 200
        # - ...
        pretty_informative_taxes = Markup()
        for tax in informative_taxes:
            line = ", ".join(f"{key}: {value}" for key, value in tax.items())
            pretty_informative_taxes += Markup("<li>%s</li>") % line

        self.with_context(no_new_invoice=True).message_post(
            body=Markup("%s<ul>%s</ul>")
            % (_("Informative taxes:"), pretty_informative_taxes or Markup("<li>%s</li>") % _("N/A"))
        )

    def _l10n_br_remove_informative_taxes(self, payload):
        # Remove informative taxes when submitting the invoice. These informative taxes change after invoice posting,
        # based on when a customer pays. These need to be handled manually in a separate misc journal entry when needed,
        # and should not be included in the legal XML and PDF.
        for line in payload.get("lines", []):
            line["taxDetails"] = [
                detail for detail in line["taxDetails"] if detail["taxImpact"]["impactOnFinalPrice"] != "Informative"
            ]

        tax_highlights = payload.get("summary", {}).get("taxImpactHighlights", {})
        if "informative" in tax_highlights:
            for informative_tax in tax_highlights.get("informative", []):
                del payload["summary"]["taxByType"][informative_tax["taxType"]]

            del tax_highlights["informative"]

    def _l10n_br_type_specific_header(self, tax_data_header):
        """Pieces of the header that change depending on whether the transaction is a service or goods one."""
        if self.l10n_br_is_service_transaction:
            return {
                "rpsNumber": self.l10n_latam_document_number,
                "rpsSerie": self.journal_id.l10n_br_invoice_serial,
            }
        else:
            goods_nfe, goods_goal = self._l10n_br_edi_get_goods_values()
            return {
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
            }

    def _l10n_br_get_location_dict(self, partner):
        return {
            "name": partner.name,
            "businessName": partner.name,
            "type": self._l10n_br_get_partner_type(partner),
            "federalTaxId": partner.vat,
            "cityTaxId": partner.l10n_br_im_code,
            "stateTaxId": partner.l10n_br_ie_code,
            "suframa": partner.l10n_br_isuf_code,
            "address": {
                "neighborhood": partner.street2,
                "street": partner.street_name,
                "zipcode": partner.zip,
                "cityName": partner.city,
                "state": partner.state_id.code,
                "countryCode": partner.country_id.l10n_br_edi_code,
                "number": partner.street_number,
                "complement": partner.street_number2,
                "phone": partner.phone,
                "email": partner.email,
            },
        }

    def _l10n_br_get_locations(self, customer, company_partner, transporter):
        locations = {
            "entity": self._l10n_br_get_location_dict(customer),
            "establishment": self._l10n_br_get_location_dict(company_partner),
        }

        if not self.l10n_br_is_service_transaction:
            locations["transporter"] = self._l10n_br_get_location_dict(transporter)

        return locations

    def _l10n_br_get_additional_info(self):
        info = self.narration and html2plaintext(self.narration)  # html2plaintext turns False into "False"
        return {
            "additionalInfo": {"otherInfo" if self.l10n_br_is_service_transaction else "complementaryInfo": info}
        }

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
        company_partner = self.company_id.partner_id

        transporter = self.l10n_br_edi_transporter_id
        is_invoice = self.move_type == "out_invoice"
        if self.l10n_br_edi_freight_model == "SenderVehicle":
            transporter = self.company_id.partner_id if is_invoice else customer
        elif self.l10n_br_edi_freight_model == "ReceiverVehicle":
            transporter = customer if is_invoice else self.company_id.partner_id

        errors.extend(self._l10n_br_edi_check_calculated_tax())
        errors.extend(self._l10n_br_edi_validate_partner(customer))
        errors.extend(self._l10n_br_edi_validate_partner(company_partner))
        errors.extend(self._l10n_br_edi_validate_partner(transporter))

        invoice_refs, error = self._l10n_br_edi_get_invoice_refs()
        if error:
            errors.append(error)

        tax_data_to_include, tax_data_header = self._l10n_br_edi_get_tax_data()
        extra_payload = {
            "header": {
                "companyLocation": self._l10n_br_edi_vat_for_api(company_partner.vat),
                **invoice_refs,
                **self._l10n_br_type_specific_header(tax_data_header),
                "locations": self._l10n_br_get_locations(
                    customer,
                    company_partner,
                    transporter,
                ),
                "payment": {
                    "paymentInfo": {
                        "paymentMode": [
                            self._l10n_br_prepare_payment_mode(),
                        ],
                    },
                },
                **self._l10n_br_get_additional_info(),
                "shippingDate": fields.Date.to_string(self.delivery_date),
            },
        }

        # extra_payload is cleaned before it's used to avoid e.g. "cityName": False or "number": "". These make
        # Avatax return various errors: e.g. "Falha na estrutura enviada". This is to avoid having lots of if
        # statements.
        deep_update(payload, deep_clean(extra_payload))

        # This adds the "lines" and "summary" dicts received during tax calculation.
        payload.update(tax_data_to_include)

        self._l10n_br_log_informative_taxes(payload)

        if self.l10n_br_is_service_transaction:
            self._l10n_br_remove_informative_taxes(payload)

        return payload, errors

    def _l10n_br_get_error_from_response(self, response):
        if error := response.get("error"):
            return f"Code {error['code']}: {error['message']}"

    def _l10n_br_submit_invoice(self, invoice, payload):
        try:
            route = "submit_invoice_services" if self.l10n_br_is_service_transaction else "submit_invoice_goods"
            response = invoice._l10n_br_iap_request(route, payload)
            return response, self._l10n_br_get_error_from_response(response)
        except (UserError, InsufficientCreditError) as e:
            # These exceptions can be thrown by iap_jsonrpc()
            return None, str(e)

    def _cron_l10n_br_get_invoice_statuses(self, batch_size=10):
        pending_invoices = self.search([("l10n_br_last_edi_status", "=", "pending")], limit=batch_size + 1)
        for invoice in pending_invoices[:batch_size]:
            invoice.button_l10n_br_edi_get_service_invoice()
            if self._can_commit():
                self.env.cr.commit()

        if len(pending_invoices) > batch_size:
            self.env.ref("l10n_br_edi.ir_cron_l10n_br_edi_check_status")._trigger()

    def _l10n_br_edi_import_invoice(self, invoice, data, is_new):
        namespaces = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

        def get_xml_text(tree, xpath):
            return find_xml_value(xpath, tree, namespaces=namespaces)

        def get_xml_attribute(xpath, attribute):
            return tree.xpath(xpath, namespaces=namespaces)[0].get(attribute)

        def get_latam_document_type():
            return self.env['l10n_latam.document.type'].search([
                ('country_id.code', '=', 'BR'),
                ('code', '=', get_xml_text(tree, './/nfe:mod'))
            ], limit=1).id

        def get_partner_id(xpath, create_if_not_found=False):
            partner_tree = tree.xpath(xpath, namespaces=namespaces)
            if not partner_tree:
                return False

            Partner = self.env['res.partner']
            partner_tree = partner_tree[0]
            cnpj_id = self.env.ref('l10n_br.cnpj').id
            if cnpj := get_xml_text(partner_tree, './/nfe:CNPJ'):
                if partner := Partner.search([('l10n_latam_identification_type_id', '=', cnpj_id), ('vat', 'in', (cnpj, format_cnpj(cnpj)))], limit=1):
                    return partner.id

            cpf_id = self.env.ref('l10n_br.cpf').id
            if cpf := get_xml_text(partner_tree, './/nfe:CPF'):
                if partner := Partner.search([('l10n_latam_identification_type_id', '=', cpf_id), ('vat', 'in', (cpf, format_cpf(cpf)))], limit=1):
                    return partner.id

            if create_if_not_found:
                country_id = False
                if c_pays := get_xml_text(partner_tree, './/nfe:cPais'):
                    country_id = self.env['res.country'].search([('l10n_br_edi_code', '=', c_pays)], limit=1).id

                state_id = False
                if uf := get_xml_text(partner_tree, './/nfe:UF'):
                    state_id = self.env['res.country.state'].search([('country_id', '=', country_id), ('code', '=', uf)], limit=1).id

                city_id = False
                if x_mun := get_xml_text(partner_tree, './/nfe:xMun'):
                    city_domain = [('country_id', '=', country_id), ('name', '=ilike', x_mun)]
                    if state_id:
                        city_domain += [('state_id', '=', state_id)]

                    city_id = self.env['res.city'].search(city_domain, limit=1).id

                return Partner.create({
                    'is_company': True,
                    'vat': cnpj or cpf,
                    'l10n_latam_identification_type_id': cnpj_id if cnpj else cpf_id,
                    'name': get_xml_text(partner_tree, './/nfe:xNome'),
                    'street_name': get_xml_text(partner_tree, './/nfe:xLgr'),
                    'street_number': get_xml_text(partner_tree, './/nfe:nro'),
                    'street2': get_xml_text(partner_tree, './/nfe:xBairro'),
                    'street_number2': get_xml_text(partner_tree, './/nfe:xCpl'),
                    'city_id': city_id,
                    'state_id': state_id,
                    'zip': get_xml_text(partner_tree, './/nfe:CEP'),
                    'country_id': country_id,
                    'phone': get_xml_text(partner_tree, './/nfe:fone'),
                    'l10n_br_ie_code': get_xml_text(partner_tree, './/nfe:IE'),
                    'l10n_br_im_code': get_xml_text(partner_tree, './/nfe:IM'),
                }).id

        def get_payment_method():
            possible_values = self._fields.get('l10n_br_edi_payment_method').get_values(self.env)
            t_pag = get_xml_text(tree, './/nfe:tPag')
            return t_pag if t_pag in possible_values else '99'

        def get_freight_model():
            mod_frete = get_xml_text(tree, './/nfe:modFrete')
            return {
                '0': 'CIF',
                '1': 'FOB',
                '2': 'Thirdparty',
                '3': 'SenderVehicle',
                '4': 'ReceiverVehicle',
                '9': 'FreeShipping',
            }.get(mod_frete)

        def get_lines_vals(vendor_id):
            def get_uom_id(u_com):
                return {
                    'KG': self.env.ref('uom.product_uom_kgm'),
                    'G': self.env.ref('uom.product_uom_gram'),
                    'L': self.env.ref('uom.product_uom_litre'),
                    'M': self.env.ref('uom.product_uom_meter'),
                    'MM': self.env.ref('uom.product_uom_millimeter'),
                    'M2': self.env.ref('uom.uom_square_meter'),
                    'M3': self.env.ref('uom.product_uom_cubic_meter'),
                    'DZ': self.env.ref('uom.product_uom_dozen'),
                    'GL': self.env.ref('uom.product_uom_gal'),
                    'TON': self.env.ref('uom.product_uom_ton'),
                }.get(u_com, self.env.ref('uom.product_uom_unit')).id

            def get_product_id():
                def get_product_id_supplierinfo(supplierinfo):
                    """ Return a product.product id only if the supplierinfo refers to exactly one variant. """
                    if supplierinfo.product_id:
                        return supplierinfo.product_id.id
                    if supplierinfo.product_variant_count == 1:
                        return supplierinfo.product_tmpl_id.product_variant_id.id

                c_prod = get_xml_text(line, './/nfe:cProd')
                if vendor_id:
                    domain = [('partner_id', '=', vendor_id)]
                    if c_prod:
                        if product_id := get_product_id_supplierinfo(self.env['product.supplierinfo'].search(domain + [('product_code', '=', c_prod)], limit=1)):
                            return product_id

                    if x_prod := get_xml_text(line, './/nfe:xProd'):
                        if product_id := get_product_id_supplierinfo(self.env['product.supplierinfo'].search(domain + [('product_name', '=', x_prod)], limit=1)):
                            return product_id

                if c_prod:
                    return self.env['product.product'].search([('default_code', '=', c_prod)], limit=1).id

            vals = []
            for line in tree.xpath('.//nfe:det/nfe:prod', namespaces=namespaces):
                product_id = get_product_id()
                description = ' '.join([get_xml_text(line, './/nfe:xProd'), get_xml_text(line, './/nfe:cProd')])
                vals.append({
                    'product_id': product_id,
                    'name': False if product_id else description,
                    'quantity': get_xml_text(line, './/nfe:qCom'),
                    'product_uom_id': get_uom_id(get_xml_text(line, './/nfe:uTrib')),
                    'price_unit': get_xml_text(line, './/nfe:vUnCom'),
                    'price_total': get_xml_text(line, './/nfe:vProd'),
                    'is_imported': True,  # don't change imported price when modifying this line
                })

            return vals

        try:
            tree = etree.fromstring(data['content'])
        except (etree.ParseError, ValueError) as e:
            _logger.info("XML parsing of %s failed: %s", data['filename'], e)
            return

        # emit is required in leiauteNFe_v4.00.xsd
        vendor = get_partner_id('.//nfe:emit', create_if_not_found=True)
        invoice.write({
            'partner_id': vendor,
            'l10n_latam_document_type_id': get_latam_document_type(),
            'name': get_xml_text(tree, './/nfe:nNF'),
            'invoice_date': get_xml_text(tree, './/nfe:dhEmi'),  # ignore timezone offset, because this is a date field
            'delivery_date': get_xml_text(tree, './/nfe:dhSaiEnt'),  # ignore timezone offset, because this is a date field
            'l10n_br_access_key': get_xml_attribute('.//nfe:infNFe', 'Id'),
            'invoice_line_ids': [Command.create(line) for line in get_lines_vals(vendor)],
            'l10n_br_edi_payment_method': get_payment_method(),
            'l10n_br_edi_transporter_id': get_partner_id('.//nfe:transporta'),
            'l10n_br_edi_freight_model': get_freight_model(),
        })

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        def is_nfe(content):
            return b"<nfeProc " in content and b"<NFe " in content

        if file_data['type'] == 'xml' and is_nfe(file_data['content']):
            return self._l10n_br_edi_import_invoice

        return super()._get_edi_decoder(file_data, new=new)
