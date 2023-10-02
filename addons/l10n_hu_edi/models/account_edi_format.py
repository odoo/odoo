# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, api, models, _
from odoo.tools import float_repr, float_round
from odoo.exceptions import UserError
from lxml import etree
import socket
import logging

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_hu_edi_get_electronic_invoice_template(self, invoice):
        """This is for feature extendibility"""
        return "l10n_hu_edi.nav_online_invoice_xml_3_0"

    @api.model
    def _l10n_hu_edi_generate_xml_line_data(self, invoice):
        data = []
        for line in invoice.line_ids.filtered(lambda l: l.l10n_hu_line_number).sorted(lambda l: l.l10n_hu_line_number):
            tax = line.tax_ids.filtered(lambda l: l.l10n_hu_tax_type)
            lnchain = 0
            if invoice.reversed_entry_id:
                previous_invoices = invoice.reversed_entry_id.reversal_move_id.filtered(lambda m: m.state == "posted")
                if previous_invoices:
                    # count of all of the previous lines
                    lnchain = len(previous_invoices.mapped("line_ids").filtered(lambda li: li.l10n_hu_line_number))

            line_data = {
                "line_object": line,
                "product_object": line.product_id,
                "line_number": line.l10n_hu_line_number,
                "line_number_chain": line.l10n_hu_line_number + lnchain,
                "description": line.name,
                "nature_indicator": "OTHER",
                "vat_type": "NO-VAT",
            }

            if line.display_type == "product":
                price_unit = line.price_unit * (1 - (line.discount / 100.0))

                taxes_res = line.tax_ids.compute_all(
                    price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                )

                tax_data = {}
                for tax_data_item in taxes_res["taxes"]:
                    if tax.id == tax_data_item["id"]:
                        tax_data = tax_data_item
                        break

                line_gross = line.price_total
                line_gross_huf = float_round(line_gross * invoice.l10n_hu_currency_rate, 2)
                amount = tax_data.get("amount", 0.0)
                amount_huf = float_round(amount * invoice.l10n_hu_currency_rate, 2)

                # here, we calculate back the net: gross - vat
                line_data.update(
                    {
                        "quantity": line.quantity,
                        "uom": "PIECE",
                        "price_unit": price_unit,
                        "sum_net": line_gross - amount,
                        "sum_gross": line_gross,
                        "sum_vat": amount,
                        "sum_net_huf": line_gross_huf - amount_huf,
                        "sum_gross_huf": line_gross_huf,
                        "sum_vat_huf": amount_huf,
                    }
                )

                if line.product_id:
                    if line.product_id.type == "service":
                        line_data["nature_indicator"] = "SERVICE"
                    else:
                        line_data["nature_indicator"] = "PRODUCT"

                    if line.product_uom_id.l10n_hu_measure_unit_code:
                        line_data["uom"] = line.product_uom_id.l10n_hu_measure_unit_code
                    else:
                        line_data.update(
                            {
                                "uom": "OWN",
                                "uom_name": line.product_uom_id.name,
                            }
                        )

                # discount
                if line.discount:
                    line_data.update(
                        {
                            "discount": f"{line.discount}% kedvezmény",
                            # "discount_value": XXX,
                            "discount_rate": line.discount,
                        }
                    )

            elif line.display_type == "rounding":
                amount = invoice.invoice_cash_rounding_id.compute_difference(
                    invoice.currency_id, invoice.tax_totals["amount_total"]
                )
                line_data.update(
                    {
                        "quantity": None,
                        "price_unit": amount,
                        "sum_net": amount,
                        "sum_gross": amount,
                        "sum_vat": 0,
                        "sum_net_huf": float_round(amount * invoice.l10n_hu_currency_rate, 2),
                        "sum_gross_huf": float_round(amount * invoice.l10n_hu_currency_rate, 2),
                        "sum_vat_huf": 0,
                    }
                )
                if not tax:
                    line_data.update(
                        {
                            "vat_type": "ATK",
                            "vat_reason": "Áfa tárgyi hatályán kívül/Outside the scope of VAT",
                        }
                    )

            if tax:
                if tax.l10n_hu_tax_type == "VAT":
                    line_data.update(
                        {
                            "vat_type": tax.l10n_hu_tax_type,
                            "vat_percent": tax.amount / 100.0,
                        }
                    )
                else:
                    line_data.update(
                        {
                            "vat_type": tax.l10n_hu_tax_type[4:],
                            "vat_reason": tax.l10n_hu_tax_reason,
                        }
                    )

            # if there is no officially uom, than dont upload it
            if not line.product_uom_id and "uom" in line_data:
                del line_data["uom"]

            data.append(line_data)
        return data

    @api.model
    def _l10n_hu_edi_generate_xml_tax_summary_data(self, invoice):
        """
        We have to recalculate the tax summary because the Hungarian tax authorities have a different meaning of net
        than the one stored in Odoo. Because according to Hungarian standards, there can be exactly one VAT entry on
        a line item, its rate is the amount of VAT, and everything else is the net.
        So the formula:
            * find the VAT object (if any), get its amount
            * net = gross - VAT
        """
        tax_tbl = self.env["account.tax"].sudo()

        sum_net = 0
        sum_net_huf = 0
        sum_gross = 0
        sum_gross_huf = 0
        sum_vat = 0
        sum_vat_huf = 0
        by_vat = {}

        for line in invoice.line_ids.filtered(lambda l: l.display_type in ("product", "rounding")):
            line_gross = line.price_total
            line_gross_huf = float_round(line_gross * invoice.l10n_hu_currency_rate, 2)
            amount = 0
            key = "NO-VAT"
            vat_type = "NO-VAT"
            tax = None

            if line.display_type == "rounding":
                line_gross = invoice.invoice_cash_rounding_id.compute_difference(
                    invoice.currency_id, invoice.tax_totals["amount_total"]
                )
                line_gross_huf = float_round(line_gross * invoice.l10n_hu_currency_rate, 2)
                if len(line.tax_ids) == 1:
                    tax = line.tax_ids
                else:
                    tax = self.env["account.tax"].search(
                        [
                            ("l10n_hu_tax_type", "=", "VAT-ATK"),
                            ("company_id", "=", invoice.company_id.id),
                        ],
                        limit=1,
                    )
                    if not tax:
                        raise UserError(_("Please create an ATK (outside the scope of the VAT Act) type of tax!"))
                vat_type = "ATK"
                key = "VAT-ATK:rounding"

            elif line.tax_ids:
                line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))

                taxes_res = line.tax_ids.compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                )

                for tax_data in taxes_res["taxes"]:
                    tax_obj = tax_tbl.browse(tax_data["id"])

                    if tax_obj.l10n_hu_tax_type:
                        tax = tax_obj
                        vat_type = tax_obj.l10n_hu_tax_type
                        if vat_type == "VAT":
                            key = f"VAT/{tax_obj.amount}"
                        if vat_type.startswith("VAT-"):
                            vat_type = vat_type[4:]
                            key = f"{tax_obj.l10n_hu_tax_type}:{tax_obj.l10n_hu_tax_reason}"

                        amount = tax_data["amount"]
                        break

            amount_huf = float_round(amount * invoice.l10n_hu_currency_rate, 2)
            base = line_gross - amount
            base_huf = line_gross_huf - amount_huf

            by_vat.setdefault(key, {"vat_type": vat_type, "net": 0, "net_huf": 0, "amount": 0, "amount_huf": 0})
            by_vat[key]["net"] += base
            by_vat[key]["net_huf"] += base_huf
            by_vat[key]["amount"] += amount
            by_vat[key]["amount_huf"] += amount_huf
            if tax:
                if tax.l10n_hu_tax_type == "VAT":
                    by_vat[key]["vat_percent"] = tax.amount / 100.0
                elif tax.l10n_hu_tax_reason:
                    by_vat[key]["vat_reason"] = tax.l10n_hu_tax_reason
            elif line.display_type == "rounding":
                by_vat[key]["vat_reason"] = "Áfa tárgyi hatályán kívül/Outside the scope of VAT"

            sum_net += base
            sum_gross += line_gross
            sum_net_huf += base_huf
            sum_gross_huf += line_gross_huf
            sum_vat += amount
            sum_vat_huf += amount_huf

        data = {
            "net": sum_net,
            "net_huf": sum_net_huf,
            "gross": sum_gross,
            "gross_huf": sum_gross_huf,
            "vat": sum_vat,
            "vat_huf": sum_vat_huf,
            "tax_summary": [by_vat[x] for x in by_vat],
        }

        return data

    @api.model
    def _l10n_hu_edi_generate_xml_data(self, invoice):
        conn_obj = self.env["l10n_hu.nav_communication"]

        def format_text(value, maxlen=None):
            # replace illegal characters
            # TODO: strip out illegal characters
            value = value.replace("\n", " ")
            if maxlen:
                value = value[:maxlen]
            return value

        def format_monetary(number, currency):
            # Format the monetary values to avoid trailing decimals (e.g. 90.85000000000001).
            reprnum = float_repr(float_round(number, currency.decimal_places), currency.decimal_places)
            if "." in reprnum:
                pre, end = reprnum.split(".")
                if int(end) == 0:
                    reprnum = pre
            if "." in reprnum:
                reprnum = reprnum.rstrip("0")
            return reprnum

        def format_float(value, prec=None):
            if not prec:
                prec = 2
            reprnum = float_repr(value, prec)
            if "." in reprnum:
                reprnum = reprnum.rstrip("0")
            if reprnum.endswith("."):
                reprnum = reprnum.rstrip(".")
            return reprnum

        company_bank = None
        if "out" in invoice.move_type and invoice.partner_bank_id:
            company_bank = invoice.partner_bank_id
        elif invoice.company_id.partner_id.bank_ids:
            company_bank = invoice.company_id.partner_id.bank_ids[0]

        return {
            "invoice": invoice,
            "sign": "refund" in invoice.move_type and -1.0 or 1.0,
            "company_partner": invoice.company_id.partner_id,
            "invoice_partner": invoice.partner_id.commercial_partner_id,
            "shipping_partner": invoice.partner_shipping_id,
            "sales_partner": invoice.user_id,
            "company_partner_bank_account": company_bank,
            "invoice_partner_bank_account": invoice.partner_id.commercial_partner_id.bank_ids
            and invoice.partner_id.commercial_partner_id.bank_ids[0],
            "line_data": self._l10n_hu_edi_generate_xml_line_data(invoice),
            "tax_summary_data": self._l10n_hu_edi_generate_xml_tax_summary_data(invoice),
            "eu_country_codes": self.env.ref("base.europe").country_ids.mapped("code"),
            "einvoice_hash": None,
            "currency_huf": self.env["res.currency"].search([("name", "=", "HUF")], limit=1),
            "format_text": format_text,
            "format_bool": conn_obj._gen_nav_format_bool,
            "format_date": conn_obj._gen_nav_format_date,
            "format_datetime": conn_obj._gen_nav_format_timestamp,
            "format_monetary": format_monetary,
            "format_float": format_float,
            "float_round": float_round,
        }

    def _l10n_hu_edi_generate_xml(self, invoice, minimisation=True):
        """Renders the XML that will be sent to NAV."""

        xml_content_unformatted = self.env["ir.qweb"]._render(
            self._l10n_hu_edi_get_electronic_invoice_template(invoice),
            self._l10n_hu_edi_generate_xml_data(invoice),
        )
        if minimisation:
            # XML minimalisation
            parser = etree.XMLParser(remove_blank_text=True)
            elem = etree.XML(xml_content_unformatted, parser=parser)
            xml_content = etree.tostring(elem)
        else:
            xml_content = xml_content_unformatted.encode()

        self.env["l10n_hu.nav_communication"]._xml_validator(xml_content, "InvoiceData")

        return b'<?xml version="1.0" encoding="utf-8"?>\n' + xml_content

    def _l10n_hu_post_invoice_step_1(self, invoice):
        """Sends the xml to NAV."""
        # == Generate XML ==
        xml_filename = "invoice_data_navxml.xml"
        xml = self._l10n_hu_edi_generate_xml(invoice)
        attachment = self.env["ir.attachment"].create(
            {
                "name": xml_filename,
                "res_id": invoice.id,
                "res_model": invoice._name,
                "type": "binary",
                "raw": xml,
                "mimetype": "application/xml",
                "description": _("Hungarian invoice NAV 3.0 XML generated for the %s document.", invoice.name),
            }
        )

        # == Upload ==
        conn_obj = self.env["l10n_hu.nav_communication"]._get_best_communication(invoice.company_id)
        try:
            response = conn_obj.do_invoice_upload(invoice)
        except Exception as e:  # noqa: BLE001
            _logger.error(e)
            if isinstance(e, socket.timeout):
                return {"error": _("Connection to NAV servers timed out."), "blocking_level": "warning"}
            return {"error": str(e), "blocking_level": "error"}

        if response["response_tag"] == "GeneralErrorResponse":
            return {"error": f"{response['message']} ({response['errorCode']})", "blocking_level": "error"}

        elif response["response_tag"] == "GeneralExceptionResponse":
            msgs = []
            for msg in response["technicalValidationMessages"]:
                msgs.append(f"{msg['message']} ({msg['validationResultCode']},{msg['validationErrorCode']})")
            return {"error": "\n".join(msgs), "blocking_level": "error"}

        elif response["response_tag"] == "ManageInvoiceResponse":
            transaction_tbl = self.env["l10n_hu.upload_transaction"].sudo()
            tr_obj = transaction_tbl.create(
                {
                    "invoice_id": invoice.id,
                    "request_code": response["requestId"],
                    "user": conn_obj.username,
                    "version": "3.0",
                    "transaction_code": response["transactionId"],
                    "reply_status": "sent",
                    "production_mode": conn_obj.state == "prod",
                }
            )
            invoice.l10n_hu_actual_transaction_id = tr_obj

            main_message = _("Invoice submission succeeded. Waiting for answer.")
            transaction_message = _("Transaction")
            invoice.with_context(no_new_invoice=True).message_post(
                body=f"{main_message}<br/>{transaction_message}: {invoice.l10n_hu_actual_transaction_id._get_html_link()}",
                attachment_ids=attachment.ids,
            )

        return {"attachment": attachment}

    def _l10n_hu_post_invoice_step_2(self, invoice):
        """Download the response from NAV."""

        conn_obj = self.env["l10n_hu.nav_communication"].search(
            [
                ("company_id", "=", invoice.company_id.id),
                ("username", "=", invoice.l10n_hu_actual_transaction_id.user),
            ]
        )
        if not conn_obj:
            return {
                "error": _(
                    "The NAV user is missing: %s. The invoice upload status can only be checked with the same user!",
                    invoice.l10n_hu_actual_transaction_id.user,
                ),
                "blocking_level": "warning",
            }

        invoice_state_response = conn_obj.do_query_transaction(invoice.l10n_hu_actual_transaction_id.transaction_code)
        response = {}
        if invoice_state_response["funcCode"] == "OK":
            inv_data = invoice_state_response["invoices"][1]

            deny = False
            main_message = None
            messages = []
            detailed_messages = []
            info = False
            warn = False

            if inv_data["invoiceStatus"] == "DONE":
                response["success"] = True
                main_message = _("The invoice was successfully accepted by the NAV.")

            elif inv_data["invoiceStatus"] == "ABORTED":
                deny = True
                main_message = _("The invoice was rejected by the NAV, the invoice is invalid!")

            else:
                return {}

            def format_dict_to_html(data, header=None):
                ll = ["<ul>"]
                if header:
                    ll.insert(0, f"<h3>{header}</h3>")
                for key in data:
                    if isinstance(data[key], dict):
                        ll.append(f"<li>{key}: {format_dict_to_html(data[key])}</li>")
                    elif isinstance(data[key], list):
                        ll.append(f"<li>{key}: {format_list_to_html(data[key])}</li>")
                    else:
                        ll.append(f"<li>{key}: {data[key]}</li>")
                ll.append("</ul>")
                return "".join(ll)

            def format_list_to_html(data, header=None):
                ll = ["<ol>"]
                if header:
                    ll.insert(0, f"<h3>{header}</h3>")
                for item in data:
                    if isinstance(item, dict):
                        ll.append(f"<li>{format_dict_to_html(item)}</li>")
                    elif isinstance(item, list):
                        ll.append(f"<li>{format_list_to_html(item)}</li>")
                    else:
                        ll.append(f"<li>{item}</li>")
                ll.append("</ol>")
                return "".join(ll)

            if inv_data.get("businessValidationMessages"):
                detailed_messages.append("<h2>%s</h2>" % _("Business Validation Messages"))

            for message in inv_data.get("businessValidationMessages", []):
                if message["validationResultCode"] == "INFO":
                    label = _("Info")
                    info = True
                elif message["validationResultCode"] == "WARN":
                    label = _("Warning")
                    warn = True
                elif message["validationResultCode"] == "ERROR":
                    label = _("Error")
                messages.append(f"<div>{label}: {message['message']}</div>")

                err_code = message["validationErrorCode"]
                del message["validationResultCode"]
                del message["validationErrorCode"]
                detailed_messages.append(format_dict_to_html(message, f"{label}: {err_code}"))

            if inv_data.get("technicalValidationMessages"):
                detailed_messages.append("<h2>%s</h2>" % _("Technical Validation Messages"))

            for message in inv_data.get("technicalValidationMessages", []):
                if message["validationResultCode"] == "INFO":
                    label = _("Info")
                    info = True
                elif message["validationResultCode"] == "WARN":
                    label = _("Warning")
                    warn = True
                elif message["validationResultCode"] == "ERROR":
                    label = _("Error")
                messages.append(f"<div>{label}: {message['message']}</div>")

                err_code = message["validationErrorCode"]
                del message["validationResultCode"]
                del message["validationErrorCode"]
                detailed_messages.append(format_dict_to_html(message, f"{label}: {err_code}"))

            # write to invoice chatter
            msg = ["<div><b>", main_message, "</b>"]
            if messages:
                msg += ["<ul><li>", "</li><li>".join(messages), "</li></ul>"]
            msg += ["</div>"]
            invoice.with_context(no_new_invoice=True).message_post(
                body="".join(msg),
            )

            # write into NAV Transaction Object
            reply_status = "ok"
            if deny:
                reply_status = "error"
            elif warn:
                reply_status = "ok_w"
            elif info:
                reply_status = "ok_i"

            invoice.l10n_hu_actual_transaction_id.sudo().write(
                {
                    "reply_status": reply_status,
                    "reply_time": fields.Datetime.now(),
                    "reply_message": "\n".join(detailed_messages),
                }
            )

            if deny:
                # TODO: auto set back to draft state?
                # invoice.button_draft()
                return {
                    "error": "\n".join(messages),
                    "blocking_level": "error",
                }

        return response

    def _l10n_hu_edi_check_invoice_for_errors(self, invoice):
        error_message = []

        if invoice.journal_id.restrict_mode_hash_table:
            error_message.append(_("Hash protection on journal is not compatible with Hungarin Invoicing solution."))

        company_partner = invoice.company_id.partner_id
        if not company_partner.country_id or company_partner.country_id.code != "HU":
            return [_("Only Hungarian companies can use the Hungarian invoicing function!")]

        if not company_partner.vat:
            if invoice.is_sale_document(include_receipts=True):
                error_message.append(_("Please set issuer VAT number!"))
            else:
                error_message.append(_("Please set customer VAT number!"))
        if not company_partner.zip or not company_partner.city or not company_partner.street:
            if invoice.is_sale_document(include_receipts=True):
                error_message.append(_("Please set issuer address properly!"))
            else:
                error_message.append(_("Please set customer address properly!"))

        if company_partner.l10n_hu_is_vat_group_member and not company_partner.l10n_hu_vat_group_member:
            error_message.append(
                _(
                    "Your company is selected to be member of a TAX Group, but no Group Membership VAT Number is provided!"
                )
            )

        invoice_partner = invoice.partner_id.commercial_partner_id
        if invoice_partner.is_company:
            if not invoice_partner.country_id:
                error_message.append(_("Missing country for partner!"))

            else:
                eu_country_codes = set(self.env.ref("base.europe").country_ids.mapped("code"))
                if invoice_partner.country_code in eu_country_codes and not invoice_partner.vat:
                    error_message.append(_("Missing VAT number for partner!"))

            if (
                invoice_partner.country_code == "HUF"
                and invoice_partner.l10n_hu_is_vat_group_member
                and not invoice_partner.l10n_hu_vat_group_member
            ):
                error_message.append(
                    _(
                        "The partner is selected to be member of a TAX Group, but no Group Membership VAT Number is provided!"
                    )
                )

        # Incoming Invoices
        if invoice.is_purchase_document(include_receipts=True):
            # the currency rate and the delivery date is coming from the issuer
            if not invoice.l10n_hu_currency_rate and invoice.currency_id.code != "HUF":
                error_message.append(_("The currency rate used on the invoice is not specified!"))
            if not invoice.delivery_date:
                error_message.append(_("The delivery date on the invoice is not specified!"))

        for line in invoice.invoice_line_ids.filtered(lambda l: l.display_type in ("product", "rounding")):
            tax = line.tax_ids.filtered(lambda t: t.l10n_hu_tax_type)
            # rounding line can have no VAT, we will upload it anyway to NAV
            if len(tax) == 0 and line.display_type == "product":
                error_message.append(_("You must select a VAT type of tax for line: %s!", line.name))
            if len(tax) > 1:
                error_message.append(_("You should only have one VAT type of tax for line: %s!", line.name))
            if line.display_type == "rounding" and tax.l10n_hu_tax_type != "VAT-ATK":
                error_message.append(_("The rounding line can only contain VAT with type ATK!"))

        add_chain_error = False
        if invoice.reversed_entry_id:
            if invoice.reversed_entry_id.reversed_entry_id:
                error_message.append(_("You cannot reverse a storno invoice!"))

            if invoice.reversed_entry_id.state != "posted":
                error_message.append(_("You cannot post a refund invoice for a not posted invoice!"))

            if (
                not invoice.reversed_entry_id.l10n_hu_actual_transaction_id
                or "ok" not in invoice.reversed_entry_id.l10n_hu_actual_transaction_id.reply_status
            ):
                add_chain_error = True

            for inv in invoice.reversed_entry_id.reversal_move_id.filtered(
                lambda i: i.state == "posted" and i.id != invoice.id
            ):
                if not inv.l10n_hu_actual_transaction_id or "ok" not in inv.l10n_hu_actual_transaction_id.reply_status:
                    add_chain_error = True

        if add_chain_error:
            error_message.append(
                _(
                    "The next invoice in the invoice chain cannot be issued until all invoices in the chain have been sent to the NAV!"
                )
            )

        return error_message

    # -------------------------------------------------------------------------
    # BUSINESS FLOW: EDI
    # -------------------------------------------------------------------------

    def _needs_web_services(self):
        # EXTENDS account_edi
        self.ensure_one()
        return self.code == "hun_nav_3_0" or super()._needs_web_services()

    def _is_compatible_with_journal(self, journal):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code != "hun_nav_3_0":
            return super()._is_compatible_with_journal(journal)
        return journal.type in ["sale", "purchase"] and journal.country_code == "HU"

    def _is_enabled_by_default_on_journal(self, journal):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code == "hun_nav_3_0":
            return journal.type in ["sale", "purchase"] and journal.country_code == "HU"
        return super()._is_enabled_by_default_on_journal(journal)

    def _get_move_applicability(self, move):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code != "hun_nav_3_0":
            return super()._get_move_applicability(move)

        # Determine on which invoices the EDI must be generated.
        if move.country_code == "HU" and move.move_type in ("out_invoice", "out_refund"):
            if move.l10n_hu_actual_transaction_id:
                return {
                    "post": self._l10n_hu_edi_post_invoice_step_2,
                    "edi_content": self._l10n_hu_edi_generate_xml,
                    # "cancel": self._l10n_hu_edi_cancel_invoice,
                }
            else:
                return {
                    "post": self._l10n_hu_edi_post_invoice_step_1,
                    "edi_content": self._l10n_hu_edi_generate_xml,
                    # "cancel": self._l10n_hu_edi_cancel_invoice,
                }

    def _l10n_hu_edi_post_invoice_step_1(self, invoice):
        return {invoice: self._l10n_hu_post_invoice_step_1(invoice)}

    def _l10n_hu_edi_post_invoice_step_2(self, invoice):
        return {invoice: self._l10n_hu_post_invoice_step_2(invoice)}

    def _l10n_hu_edi_cancel_invoice(self, invoice):
        return {invoice: {"success": True}}

    def _check_move_configuration(self, move):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code != "hun_nav_3_0":
            return super()._check_move_configuration(move)

        error_message = self._l10n_hu_edi_check_invoice_for_errors(move)
        return error_message
