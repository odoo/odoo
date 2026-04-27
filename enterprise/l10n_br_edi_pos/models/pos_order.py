# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import re
from collections import defaultdict
from hashlib import sha1

from markupsafe import Markup

from odoo import models, api, _, fields, Command
from odoo.addons.iap import InsufficientCreditError
from odoo.exceptions import UserError, ValidationError


# Copied from account.external.tax.mixin in l10n_br_edi
def deep_update(d, u):
    """Like {}.update but handles nested dicts recursively. Based on https://stackoverflow.com/a/3233356."""
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


# Copied from account.external.tax.mixin in l10n_br_edi
def deep_clean(d):
    """Recursively removes keys with a falsy value in dicts. Based on https://stackoverflow.com/a/48152075."""
    cleaned_dict = {}
    for k, v in d.items():
        if isinstance(v, dict):
            v = deep_clean(v)
        if v:
            cleaned_dict[k] = v
    return cleaned_dict or None


class PosOrder(models.Model):
    _name = "pos.order"
    _inherit = ["pos.order", "account.external.tax.mixin"]

    l10n_br_edi_avatax_data = fields.Json(
        help="Brazil: technical field that remembers the last tax summary returned by Avatax.", copy=False
    )
    l10n_br_avatax_error = fields.Text(
        "Brazil Avatax Error",
        copy=False,
        readonly=True,
        help="Brazil: error details for orders in the 'error' state.",
    )
    l10n_br_last_avatax_status = fields.Selection(
        [
            ("accepted", "Accepted"),
            ("error", "Error"),
        ],
        string="Brazil Avatax Status",
        copy=False,
        tracking=True,
        readonly=True,
        help="Brazil: the state of the most recent e-invoicing attempt.",
    )
    l10n_br_edi_number = fields.Char(
        "NFC-e Number", compute="_compute_l10n_br_edi_number", help="Brazil: NFC-e number linked to this order."
    )
    l10n_br_access_key = fields.Char(
        "Access Key",
        copy=False,
        readonly=True,
        help="Brazil: access key associated with the electronic document. Can be used to get invoice information directly from the government.",
    )
    l10n_br_edi_protocol_authorization_number = fields.Char(
        "Protocol Authorization Number",
        copy=False,
        readonly=True,
        help="Brazil: the protocol authorization number of the e-invoice.",
    )
    l10n_br_edi_authorization_date = fields.Char(
        "Authorization Date", copy=False, readonly=True, help="Brazil: the authorization date of the e-invoice."
    )
    l10n_br_edi_series = fields.Char(
        "Series",
        readonly=True,
        copy=False,
        help="Brazil: series number used for this order.",
    )

    # Technical field holding the e-invoice PDF data for security reasons.
    l10n_br_edi_pdf_attachment_file = fields.Binary(
        string="Brazil E-Invoice PDF File",
        copy=False,
        attachment=True,
    )
    # Technical field holding the e-invoice XML data for security reasons.
    l10n_br_edi_xml_attachment_file = fields.Binary(
        string="Brazil E-Invoice XML File",
        copy=False,
        attachment=True,
    )

    @api.depends("name")
    def _compute_l10n_br_edi_number(self):
        """Use the longest, rightmost contiguous string of digits as the invoice number. E.g., for Shop 01/1234 the number
        will be 1234. This number can be adjusted with the l10n_br_nfce_next_number field on pos.config, and must be unique
        in combination with l10n_br_invoice_serial."""
        pattern = re.compile(r"\d*$")
        for order in self:
            order.l10n_br_edi_number = pattern.search(order.name).group(0).zfill(9)

    def _get_date_for_external_taxes(self):
        """Returns the transactionDate. This should be the time at which the transaction happens, i.e., now. If it's more
        than 5 minutes in the past, we get an error."""
        return fields.Datetime.context_timestamp(self, fields.Datetime.now())

    @api.depends("config_id.l10n_br_is_nfce")
    def _compute_l10n_br_is_avatax(self):
        """account.external.tax.mixin override. Don't rely on fiscal positions for the POS."""
        for order in self:
            order.l10n_br_is_avatax = order.config_id.l10n_br_is_nfce

    def _get_and_set_external_taxes_on_eligible_records(self):
        """account.external.tax.mixin override."""
        eligible_orders = self.filtered(lambda order: order.l10n_br_is_avatax and order.l10n_br_last_avatax_status != "accepted")
        for order in eligible_orders:
            try:
                order._set_external_taxes(*order._get_external_taxes())
            except (UserError, ValidationError) as e:  # Don't block the POS
                order.l10n_br_last_avatax_status = "error"
                order.l10n_br_avatax_error = str(e)
            else:
                order.l10n_br_last_avatax_status = False
                order.l10n_br_avatax_error = False

        return super()._get_and_set_external_taxes_on_eligible_records()

    def _get_lines_eligible_for_external_taxes(self):
        """account.external.tax.mixin override."""
        if not self.l10n_br_is_avatax:
            return super()._get_lines_eligible_for_external_taxes()

        return self.lines

    def _get_line_data_for_external_taxes(self):
        """account.external.tax.mixin override."""
        if not self.l10n_br_is_avatax:
            return super()._get_line_data_for_external_taxes()

        res = []
        for line in self._get_lines_eligible_for_external_taxes():
            res.append(
                {
                    "id": line.id,
                    "product_id": line.product_id,
                    "qty": line.qty,
                    "price_unit": line.price_unit,
                    "discount": line.discount,
                }
            )
        return res

    def _set_external_taxes(self, mapped_taxes, summary):
        """account.external.tax.mixin override. Since taxes are always fully included, amount_total won't change."""
        if not self.l10n_br_is_avatax:
            return super()._set_external_taxes(mapped_taxes, summary)

        for line, detail in mapped_taxes.items():
            line.tax_ids = detail["tax_ids"]
            line.price_subtotal = detail["total"]
            line.price_subtotal_incl = detail["tax_amount"] + detail["total"]

        # cannot use _onchange_amount_all because it uses AccountTax._compute_all() to compute taxes.
        for order in self:
            order.amount_total = sum(line.price_subtotal_incl for line in order.lines)
            order.amount_tax = sum(line.price_subtotal_incl - line.price_subtotal for line in order.lines)

    def _l10n_br_get_operation_type(self):
        """account.external.tax.mixin override. POS is always "sale of goods"."""
        return self.env.ref("l10n_br_avatax.operation_type_1").technical_name

    def _l10n_br_do_edi(self, save_avalara_pdf=False):
        """Do both tax calculation and EDI in one step. Unlike for other models, we don't support the in-between state
        of successful tax calculation and failed EDI to simplify things."""

        # Don't do EDI for refunds, this should happen manually through account.move.
        orders_to_edi = self.filtered(lambda order: order.l10n_br_is_avatax and not order.refunded_order_id)
        original_order_amounts = {res["id"]: res for res in orders_to_edi.read(["amount_total", "amount_tax"])}
        original_line_amounts = {res["id"]: res for res in orders_to_edi.lines.read(["price_subtotal", "price_subtotal_incl"])}

        orders_to_edi._get_and_set_external_taxes_on_eligible_records()
        for order in orders_to_edi:
            if order.l10n_br_last_avatax_status == "error":
                continue  # failed tax calculation above

            if errors := order._l10n_br_edi_send(save_avalara_pdf=save_avalara_pdf):
                order.l10n_br_avatax_error = "\n".join(errors)
                order.l10n_br_edi_avatax_data = False

                # Clear all taxes if EDI fails. For POS we consider tax calculation and EDI a single step. No savepoint
                # is used because we need to save some data (l10n_br_avatax_error, ...), and this is simple enough.
                order.write(original_order_amounts[order.id])
                for line in order.lines:
                    line.tax_ids = False
                    line.write(original_line_amounts[line.id])

    def _prepare_invoice_vals(self):
        """Override. Refunds will be electronically invoiced through a normal account.move because it's not possible to
        do a salesReturn for NFC-e."""
        res = super()._prepare_invoice_vals()
        if self.l10n_br_is_avatax and self.refunded_order_id:
            fp = self.env["account.fiscal.position"].search([("l10n_br_is_avatax", "=", True)], limit=1).id
            res.update(
                {
                    "fiscal_position_id": fp,
                    # We can only assign a single payment method to the invoice, take the first one.
                    "l10n_br_edi_payment_method": self.payment_ids[0].payment_method_id.l10n_br_payment_method,
                }
            )

        return res

    def _get_invoice_post_context(self):
        """Override. Taxes will change, if we skip_invoice_sync then the move will be unbalanced."""
        res = super()._get_invoice_post_context()
        if self.l10n_br_is_avatax:
            res.pop("skip_invoice_sync", False)
        return res

    def action_pos_order_invoice(self):
        """Override."""
        if self.l10n_br_is_avatax:
            if not self.refunded_order_id:
                raise UserError(_("You cannot invoice NFC-e orders."))

            if not self.partner_id:
                raise ValidationError(_("NF-e refunds require a customer."))

        return super().action_pos_order_invoice()

    def button_l10n_br_edi(self):
        """We save the Avalara receipt PDF in cases where a customer invoices manually from the backend."""
        self._l10n_br_do_edi(save_avalara_pdf=True)

    @api.model
    def sync_from_ui(self, orders):
        """Entrypoint for EDI through the POS. Launch EDI for all paid orders when they are received in the backend. Amend
        the response sent back to the POS after EDI to include fields needed for the receipt."""
        result = super().sync_from_ui(orders)

        # all orders in a single sync_from_ui call will belong to the same session
        if (
            len(orders) > 0
            and orders[0].get("session_id")
            and self.env["pos.session"].browse(orders[0]["session_id"]).config_id.l10n_br_is_nfce
        ):
            paid_orders = [order["id"] for order in result["pos.order"] if order["state"] == "paid"]
            self.env["pos.order"].browse(paid_orders)._l10n_br_do_edi()

            for order in result["pos.order"]:
                extra_fields_needed_in_pos = [
                    "l10n_br_last_avatax_status",
                    "l10n_br_access_key",
                    "l10n_br_edi_avatax_data",
                    "l10n_br_edi_protocol_authorization_number",
                    "l10n_br_edi_authorization_date",
                    "l10n_br_avatax_error",
                ]
                order_db = self.env["pos.order"].browse(order["id"])
                order.update(order_db.read(extra_fields_needed_in_pos)[0])

        return result

    def _l10n_br_call_avatax_taxes(self):
        """Override to store the retrieved Avatax data."""
        document_to_response = super()._l10n_br_call_avatax_taxes()

        for document, response in document_to_response.items():
            if not self._l10n_br_get_error_from_response(response):
                document.l10n_br_edi_avatax_data = {
                    "header": response.get("header"),
                    "lines": response.get("lines"),
                    "summary": response.get("summary"),
                }

        return document_to_response

    def _l10n_br_get_invoice_refs(self):
        """Override. Returns a reference sent for the initial order."""
        refunded_order = self.refunded_order_id
        if not refunded_order:
            return {}

        if refunded_order.l10n_br_last_avatax_status != "accepted" or not refunded_order.l10n_br_access_key:
            raise ValidationError(
                _(
                    "%(order_name)s must be successfully invoiced before invoicing this refund.",
                    order_name=refunded_order.display_name,
                )
            )

        return {
            "invoicesRefs": [
                {
                    "type": "refNFe",
                    "refNFe": refunded_order.l10n_br_access_key,
                }
            ]
        }

    def _l10n_br_edi_get_tax_data(self):
        """Copy of account.move. Due to Avalara bugs they're unable to resolve we have to change their tax calculation response before
        sending it back to them. This returns a tuple with what to include in the request ("lines" and "summary")
        and the header (separate because it shouldn't be included)."""
        # These return errors when null in /v3/invoices
        keys_to_remove_when_null = ("ruleId", "ruleCode")

        tax_calculation_response = self.l10n_br_edi_avatax_data
        for line in tax_calculation_response.get("lines", []):
            for detail in line.get("taxDetails", []):
                for key in keys_to_remove_when_null:
                    if key in detail and detail[key] is None:
                        del detail[key]

        return tax_calculation_response, tax_calculation_response.pop("header")

    def _l10n_br_edi_vat_for_api(self, vat):
        """Copy of account.move."""
        # Typically users enter the VAT as e.g. "xx.xxx.xxx/xxxx-xx", but the API errors on non-digit characters
        return "".join(c for c in vat or "" if c.isdigit())

    def _l10n_br_edi_get_goods_values(self):
        """Returns the appropriate (finNFe, goal) tuple for the goods section in the header."""
        return 1, "Normal"

    def _l10n_br_prepare_payment_info(self):
        """Based on _l10n_br_prepare_payment_mode of account.move. The sum of all payment "value" must equal the order total.
        Because of this, we add payment methods until we reach the total. The remaining ones cannot be sent."""
        card_methods = {"03", "04", "10", "11", "12", "13", "15", "17", "18"}
        payment_modes = []
        remaining_to_pay = self.amount_total

        for payment in self.payment_ids.filtered(lambda payment: not payment.is_change):
            if remaining_to_pay <= 0:
                break

            payment_method = payment.payment_method_id.l10n_br_payment_method
            payment_mode = {
                "mode": payment_method,
                "value": min(remaining_to_pay, payment.amount),
            }
            remaining_to_pay = self.currency_id.round(remaining_to_pay - payment.amount)

            if payment_method in card_methods:
                payment_mode["cardTpIntegration"] = "2"
            elif payment_method == "99":
                payment_mode["modeDescription"] = _("Other")

            payment_modes.append(payment_mode)

        if not payment_modes:
            # Always have a payment mode value if the order is free.
            payment_modes.append({"mode": "99", "value": 0.0, "modeDescription": _("Other")})

        return {
            "change": self.currency_id.round(sum(self.payment_ids.filtered("is_change").mapped(lambda payment: -payment.amount))),
            "paymentMode": payment_modes,
        }

    def _l10n_br_get_location_dict(self, partner):
        """Copy of account.move."""
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

    def _l10n_br_get_anonymous_location_dict(self, company_partner):
        return {
            "name": "CONSUMIDOR NÃO IDENTIFICADO",
            "federalTaxId": "000.000.000-00",
            "taxRegime": "individual",
            "taxesSettings": {
                "icmsTaxPayer": False,
            },
            "activitySector": {"code": "finalConsumer"},
            "address": {
                "state": company_partner.state_id.code,
            },
        }

    def _l10n_br_get_locations(self, customer, company_partner):
        return {
            "entity": (
                self._l10n_br_get_location_dict(customer)
                if customer
                else self._l10n_br_get_anonymous_location_dict(company_partner)
            ),
            "establishment": self._l10n_br_get_location_dict(company_partner),
        }

    def _l10n_br_calculate_access_key_check_digit(self, access_key):
        """Calculate the check digit for an access key using a slight variation of the MOD 11 algorithm (0 if remainder <2)."""
        assert len(access_key) == 43
        weighted_sum = 0
        weight = 2
        for char in reversed(access_key):
            weighted_sum += int(char) * weight
            weight += 1
            if weight > 9:
                weight = 2

        remainder = weighted_sum % 11
        return 0 if remainder < 2 else (11 - remainder)

    def _l10n_br_get_cuf(self, state):
        # From http://wiki.webcgi.com.br:49735/index.php?title=C%C3%B3digos_de_cada_UF_no_Brasil_-_IBGE
        return {
            "RO": "11",
            "AC": "12",
            "AM": "13",
            "RR": "14",
            "PA": "15",
            "AP": "16",
            "TO": "17",
            "MA": "21",
            "PI": "22",
            "CE": "23",
            "RN": "24",
            "PB": "25",
            "PE": "26",
            "AL": "27",
            "SE": "28",
            "BA": "29",
            "MG": "31",
            "ES": "32",
            "RJ": "33",
            "SP": "35",
            "PR": "41",
            "SC": "42",
            "RS": "43",
            "MS": "50",
            "MT": "51",
            "GO": "52",
            "DF": "53",
        }[state.code]

    def _l10n_br_get_id_for_cnf(self):
        """Allow this to be replaced by a fixed value in tests."""
        return self.id

    def _l10n_br_generate_access_key(self):
        access_key = "".join(
            [
                f"{self._l10n_br_get_cuf(self.company_id.state_id):2.2}",
                f"{self.date_order.strftime('%y%m'):4.4}",  # dhEmi
                f"{self._l10n_br_edi_vat_for_api(self.company_id.partner_id.vat):14.14}",  # Emitter CNPJ
                f"{self.env.ref('l10n_br.dt_65').code:>02.2}",  # mod (NFC-e)
                f"{self.config_id.l10n_br_invoice_serial:>03.3}",  # serie
                self.l10n_br_edi_number,  # nNF (9 characters)
                "1",  # tpEmis, hardcoded to the "normal" type
                # cNF, an ID that uniquely identifies the order. Use the 8 least significant digits of the database ID.
                f"{self._l10n_br_get_id_for_cnf():08}"[-8:],
            ]
        )

        return f"{access_key}{self._l10n_br_calculate_access_key_check_digit(access_key)}"

    def _l10n_br_generate_nfce_qr_code(self, access_key):
        assert len(access_key) == 44

        # Already checked with RedirectWarning in _check_before_creating_new_session(), but check again to avoid
        # potential ugly traceback.
        if not self.company_id.l10n_br_edi_csc_identifier or not self.company_id.l10n_br_edi_csc_number:
            raise ValidationError(
                "Please configure a CSC ID and CSC number in the Accounting settings."
            )  # RedirectWarning not supported in POS.

        qr_code_content = "|".join(
            [
                access_key,
                "2",  # QR code version
                "1" if self.company_id.l10n_br_avalara_environment == "production" else "2",
                self.company_id.l10n_br_edi_csc_identifier.lstrip("0"),
            ]
        )

        to_hash = qr_code_content + self.company_id.l10n_br_edi_csc_number
        qr_code_content += "|" + sha1(to_hash.encode()).hexdigest()
        return self._l10n_br_get_qr_url() + qr_code_content

    def _l10n_br_get_url_key(self):
        if self.company_id.l10n_br_edi_url_key_override:
            return self.company_id.l10n_br_edi_url_key_override

        state_code = self.company_id.state_id.code

        # The exact format of these URLs is important, even though most redirect http:// to https:// changing it to https://
        # here results in errors:
        # "Endereco do site da UF da Consulta por chave de acesso diverge do previsto. [Nova url:http://www.fazenda.pr.gov.br/nfce/consulta]"
        return {
            "AC": ("http://www.sefaznet.ac.gov.br/nfce/consulta",),
            "AL": ("www.sefaz.al.gov.br/nfce/consulta",),
            "AM": ("www.sefaz.am.gov.br/nfce/consulta",),
            "AP": ("https://www.sefaz.ap.gov.br/sate/seg/SEGf_AcessarFuncao.jsp?cdFuncao=FIS_1261",),
            "BA": ("https://www.sefaz.ba.gov.br/nfce/consulta", "http://hinternet.sefaz.ba.gov.br/nfce/consulta"),
            "CE": ("http://www.sefaz.ce.gov.br/nfce/consulta",),
            "DF": ("www.fazenda.df.gov.br/nfce/consulta",),
            "ES": ("http://www.sefaz.es.gov.br/nfce/consulta",),
            "GO": ("http://www.sefaz.go.gov.br/nfce/consulta",),
            "MA": ("http://www.nfce.sefaz.ma.gov.br/portal/consultarnfce.jsp",),
            "MG": ("http://nfce.fazenda.mg.gov.br/portalnfce", "http://hinternet.sefaz.ba.gov.br/nfce/consulta"),
            "MS": ("http://www.dfe.ms.gov.br/nfce/consulta",),
            "MT": ("http://www.sefaz.mt.gov.br/nfce/consultanfce", "http://homologacao.sefaz.mt.gov.br/nfce/consultanfce"),
            "PA": ("http://www.sefa.pa.gov.br/nfce/consulta",),
            "PB": ("https://www7.sefaz.pb.gov.br/atf/seg/SEGf_AcessarFuncao.jsp?cdFuncao=FIS_1410&p=",),
            "PE": ("http://nfce.sefaz.pe.gov.br/nfce/consulta",),
            "PI": ("https://webas.sefaz.pi.gov.br/nfe/",),
            "PR": ("http://www.fazenda.pr.gov.br/nfce/consulta",),
            "RJ": ("http://www.fazenda.rj.gov.br/nfce/consulta",),
            "RN": ("https://nfce.set.rn.gov.br/portalDFE/NFCe/ConsultaNFCe.aspx",),
            "RO": ("http://www.sefin.ro.gov.br/nfce/consulta",),
            "RR": ("https://portalweb.sefaz.rr.gov.br/nfce/servlet/wp_consulta_nfce",),
            "RS": ("http://www.sefaz.rs.gov.br/nfce/consulta",),
            "SC": ("https://sat.sef.sc.gov.br/tax.net/Sat.Dfe.NFCe.Web/Consultas/ConsultaPublicaNFe.aspx",),
            "SE": ("http://www.nfce.se.gov.br/nfce/consulta", "http://www.hom.nfe.se.gov.br/nfce/consulta"),
            "SP": ("https://www.nfce.fazenda.sp.gov.br/consulta", "https://www.homologacao.nfce.fazenda.sp.gov.br/consulta"),
            "TO": ("http://www.sefaz.to.gov.br/nfce/consulta",),
        }[state_code][0 if self.company_id.l10n_br_avalara_environment == "production" else -1]

    def _l10n_br_get_qr_url(self):
        if self.company_id.l10n_br_edi_qr_url_override:
            return self.company_id.l10n_br_edi_qr_url_override

        state_code = self.company_id.state_id.code
        return {
            "AC": ("http://www.sefaznet.ac.gov.br/nfce/qrcode?p=", "http://www.hml.sefaznet.ac.gov.br/nfce/qrcode?p="),
            "AL": ("http://nfce.sefaz.al.gov.br/QRCode/consultarNFCe.jsp?p=",),
            "AM": ("https://sistemas.sefaz.am.gov.br/nfceweb/consultarNFCe.jsp?p=",),
            "AP": ("https://www.sefaz.ap.gov.br/nfce/nfcep.php?p=", "https://www.sefaz.ap.gov.br/nfcehml/nfce.php?p="),
            "BA": ("http://nfe.sefaz.ba.gov.br/servicos/nfce/qrcode.aspx?p=", "http://hnfe.sefaz.ba.gov.br/servicos/nfce/qrcode.aspx?p="),
            "CE": ("http://nfce.sefaz.ce.gov.br/pages/ShowNFCe.html?p=", "http://nfceh.sefaz.ce.gov.br/pages/ShowNFCe.html?p="),
            "DF": ("http://www.fazenda.df.gov.br/nfce/qrcode?p=",),
            "ES": ("http://app.sefaz.es.gov.br/ConsultaNFCe?p=", "http://homologacao.sefaz.es.gov.br/ConsultaNFCe?p="),
            "GO": ("https://nfeweb.sefaz.go.gov.br/nfeweb/sites/nfce/danfeNFCe?p=", "https://nfewebhomolog.sefaz.go.gov.br/nfeweb/sites/nfce/danfeNFCe?p="),
            "MA": ("nfce.sefaz.ma.gov.br/portal/consultarNFCe.jsp?p=", "homolog acao.sefaz.ma.gov.br/portal/consultarNFCe.jsp?p="),
            "MG": ("https://portalsped.fazenda.mg.gov.br/portalnfce/sistema/qrcode.xhtml?p=",),
            "MS": ("http://www.dfe.ms.gov.br/nfce/qrcode?p=",),
            "MT": ("http://www.sefaz.mt.gov.br/nfce/consultanfce?p=", "http://homologacao.sefaz.mt.gov.br/nfce/consultanfce?p="),
            "PA": ("https://appnfc.sefa.pa.gov.br/portal/view/consultas/nfce/nfceForm.seam?p=", "https://appnfc.sefa.pa.gov.br/portal-homologacao/view/consultas/nfce/nfceForm.seam?p="),
            "PB": ("http://www.sefaz.pb.gov.br/nfce?p=", "http://www.sefaz.pb.gov.br/nfcehom?p="),
            "PE": ("http://nfce.sefaz.pe.gov.br/nfce/consulta?p=", "http://nfcehomolog.sefaz.pe.gov.br/nfce/consulta?p="),
            "PI": ("http://www.sefaz.pi.gov.br/nfce/qrcode?p=",),
            "PR": ("http://www.fazenda.pr.gov.br/nfce/qrcode?p=",),
            "RJ": ("https://consultadfe.fazenda.rj.gov.br/consultaNFCe/QRCode?p=",),
            "RN": ("http://nfce.set.rn.gov.br/consultarNFCe.aspx?p=", "http://hom.nfce.set.rn.gov.br/consultarNFCe.aspx?p="),
            "RO": ("http://www.nfce.sefin.ro.gov.br/consultanfce/consulta.jsp?p=",),
            "RR": ("https://www.sefaz.rr.gov.br/nfce/servlet/qrcode?p=", "http://200.174.88.103:8080/nfce/servlet/qrcode?p="),
            "RS": ("https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx?p=",),
            "SC": ("https://sat.sef.sc.gov.br/nfce/consulta?p=", "https://hom.sat.sef.sc.gov.br/nfce/consulta?p="),
            "SE": ("http://www.nfce.se.gov.br/nfce/qrcode?p=", "http://www.hom.nfe.se.gov.br/nfce/qrcode?p="),
            "SP": ("https://www.nfce.fazenda.sp.gov.br/qrcode?p=", "https://www.homologacao.nfce.fazenda.sp.gov.br/qrcode?p="),
            "TO": ("http://www.sefaz.to.gov.br/nfce/qrcode?p=",),
        }[state_code][0 if self.company_id.l10n_br_avalara_environment == "production" else -1]

    def _l10n_br_get_calculate_payload(self):
        """Override for tax calculation payload. Add more data in this step instead of delaying it until EDI. This way
        we have it available on l10n_br_edi_avatax_data which is used for the receipt."""
        payload = super()._l10n_br_get_calculate_payload()
        customer = self.partner_id
        company_partner = self.company_id.partner_id

        goods_nfe, goods_goal = self._l10n_br_edi_get_goods_values()
        access_key = self._l10n_br_generate_access_key()
        extra_payload = {
            "header": {
                "companyLocation": self._l10n_br_edi_vat_for_api(company_partner.vat),
                "invoiceNumber": self.l10n_br_edi_number,
                "invoiceSerial": self.config_id.l10n_br_invoice_serial,
                "locations": self._l10n_br_get_locations(customer, company_partner),
                "goods": {
                    "model": self.env.ref("l10n_br.dt_65").code,
                    "tplmp": "4",  # DANFe NFC-e
                    "goal": goods_goal,
                    "finNFe": goods_nfe,
                    "urlKey": self._l10n_br_get_url_key(),
                    "nfceQrCode": self._l10n_br_generate_nfce_qr_code(access_key),
                    "tpImp": "4",
                    "indPres": "1",  # An in-person transaction.
                    "transport": {
                        "modFreight": "FreeShipping",
                    },
                },
                "payment": {
                    "paymentInfo": self._l10n_br_prepare_payment_info(),
                },
                "invoiceAccessKey": access_key,
            },
        }

        for line in payload["lines"]:
            line.pop("freightAmount")

        if not customer:
            payload["header"]["locations"].pop("entity")

        # extra_payload is cleaned before it's used to avoid e.g. "cityName": False or "number": "". These make
        # Avatax return various errors: e.g. "Falha na estrutura enviada". This is to avoid having lots of if
        # statements.
        deep_update(payload, deep_clean(extra_payload))

        return payload

    def _l10n_br_prepare_invoice_payload(self):
        errors = []

        # Don't raise because we don't want to block the POS
        try:
            # The /transaction payload requires a superset of the /calculate payload we use for tax calculation.
            payload = self._l10n_br_get_calculate_payload()
        except (UserError, ValidationError) as e:
            payload = {}
            errors.append(str(e).replace("- ", ""))

        tax_data_to_include, tax_data_header = self._l10n_br_edi_get_tax_data()
        payload["header"]["goods"]["class"] = tax_data_header.get("goods", {}).get("class")

        # This adds the "lines" and "summary" dicts received during tax calculation.
        payload.update(tax_data_to_include)
        return payload, errors

    def _l10n_br_get_error_from_response(self, response):
        """Copy of account.move."""
        if error := response.get("error"):
            return f"Code {error['code']}: {error['message']}"

    def _l10n_br_submit_invoice(self, payload):
        try:
            response = self._l10n_br_iap_request("submit_invoice_goods", payload)
            return response, self._l10n_br_get_error_from_response(response)
        except (UserError, InsufficientCreditError) as e:
            # These exceptions can be thrown by iap_jsonrpc()
            return None, str(e)

    def _l10n_br_edi_attachments_from_response(self, response, save_avalara_pdf=False):
        """Copy of account.move. Link these attachments to fields to restrict them to who can access pos.order (enforced
        by ir.attachment's check())."""
        attachments = self.env["ir.attachment"].create(
            {
                "res_model": "pos.order",
                "res_id": self.id,
                "res_field": "l10n_br_edi_xml_attachment_file",
                "name": f"{self.name}_edi.xml",
                "datas": response["xml"]["base64"],
            }
        )

        if save_avalara_pdf:
            attachments |= self.env["ir.attachment"].create(
                {
                    "res_model": "pos.order",
                    "res_id": self.id,
                    "res_field": "l10n_br_edi_pdf_attachment_file",
                    "name": f"{self.name}_edi.pdf",
                    "datas": response["pdf"]["base64"],
                }
            )

        return attachments

    def _l10n_br_edi_get_successful_message(self, adjustment_move=None):
        """Return tax summary for EDI that happens after the session is closed. This way the user can manually
        correct the accounting."""
        msg = _("E-invoice submitted successfully.")
        if not adjustment_move:
            return msg

        return msg + Markup(
            ' Adjusted taxes in <a href="#" data-oe-model="account.move" data-oe-id="%(move_id)s">%(move_name)s</a>.'
        ) % {
            "move_id": adjustment_move.id,
            "move_name": adjustment_move.name,
        }

    def _l10n_br_find_tax_for_l10n_br_avatax_code(self, l10n_br_avatax_code):
        return (
            self.env["account.tax"]
            .with_context(active_test=False)
            .search(
                [
                    ("l10n_br_avatax_code", "=", l10n_br_avatax_code),
                    ("price_include_override", "=", "tax_included"),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
                order="create_date desc",
            )
        )

    def _l10n_br_edi_adjustment_entry(self):
        """Failed EDI orders will have no taxes. If the session is already closed, this will be reflected in the closing
        journal entry. This method will be called in cases where EDI is successfully retried on orders belonging to closed
        sessions.

        This method will create a journal entry that will subtract the newly calculated taxes from the income
        account(s) (because previously the entire order amount was an Untaxed Sale) and adds the tax amounts to the
        appropriate tax accounts."""
        if self.session_id.state != "closed":
            return

        # Only depends on order_id and order_id.fiscal_position_id, so it's not accurate if tax calculation changed taxes.
        self.lines.invalidate_recordset(["tax_ids_after_fiscal_position"])
        account_to_taxes = defaultdict(float)
        adjustment_lines_vals = []
        aml_values_list = self._prepare_aml_values_list_per_nature()

        # Figure out how much total tax to remove per income account.
        for avatax_line in self.l10n_br_edi_avatax_data["lines"]:
            tax_amount = avatax_line["lineAmount"] - avatax_line["lineNetFigure"]
            line = self.env["pos.order.line"].browse(avatax_line["lineCode"])
            income_account = line.product_id._get_product_accounts()["income"] or self.config_id.journal_id.default_account_id
            account_to_taxes[income_account] += tax_amount

        # Set the removed amounts calculated above on the right product AML.
        for income_account, amount in account_to_taxes.items():
            for aml_values in aml_values_list["product"]:
                if aml_values["account_id"] == income_account.id:
                    aml_values["amount_currency"] = aml_values["balance"] = amount

        adjustment_lines_vals.extend(aml_values_list["product"])

        # Adjust the tax amounts to what Avatax returned, don't rely on what Odoo calculated.
        for l10n_br_avatax_code, details in self.l10n_br_edi_avatax_data["summary"]["taxByType"].items():
            for aml_values in aml_values_list["tax"]:
                tax = self._l10n_br_find_tax_for_l10n_br_avatax_code(l10n_br_avatax_code)
                if self.env["account.tax.repartition.line"].browse(aml_values["tax_repartition_line_id"]).tax_id == tax:
                    aml_values["amount_currency"] = aml_values["balance"] = -details["tax"]
                    aml_values["tax_base_amount"] = -details["subtotalTaxable"] + details["tax"]

        adjustment_lines_vals.extend(aml_values_list["tax"])

        adjustment_move = self.env["account.move"].create(
            {
                "ref": _("Tax adjustment for %(order_name)s", order_name=self.name),
                "journal_id": self.config_id.journal_id.id,
                "line_ids": [Command.create(line_vals) for line_vals in adjustment_lines_vals],
            }
        )
        adjustment_move._post()

        return adjustment_move

    def _l10n_br_edi_log_taxes(self):
        """There's no tax breakdown per line or order. So, we log the taxes here manually instead."""
        message = []
        has_informative_tax = False
        for line in self.l10n_br_edi_avatax_data.get('lines', []):
            tax_descriptions = []
            for tax_detail in line.get('taxDetails', []):
                # Taxes are guaranteed to be unarchived after tax calculation.
                tax = self.env['account.tax'].search([('l10n_br_avatax_code', '=', tax_detail['taxType'])], limit=1)
                is_informative = tax_detail['taxImpact']['impactOnNetAmount'] == 'Informative'
                has_informative_tax = has_informative_tax or is_informative
                tax_descriptions.append(Markup("{tax_name}{informative} - {tax_amount}").format(
                    tax_name=tax.display_name or tax_detail['taxType'],
                    tax_amount=self.currency_id.format(tax_detail['tax']),
                    informative=' (*)' if is_informative else ''
                ))

            message.append(Markup("<b>{line_name}</b><br/>{tax_descriptions}").format(
                line_name=line['itemDescriptor'].get('description'),
                tax_descriptions=Markup("<br/>").join(tax_descriptions))
            )

        if has_informative_tax:
            message.append(Markup("<i> *: ") + _("informative tax") + Markup("</i>"))

        self.message_post(body=Markup("<hr/>").join(message))

    def _l10n_br_edi_send(self, save_avalara_pdf=False):
        """Sends the e-invoice and returns an array of error strings."""
        for order in self:
            payload, validation_errors = order._l10n_br_prepare_invoice_payload()

            if validation_errors:
                return validation_errors
            else:
                response, api_error = order._l10n_br_submit_invoice(payload)
                if api_error:
                    order.l10n_br_last_avatax_status = "error"
                    return [api_error]
                else:
                    adjustment_move = order._l10n_br_edi_adjustment_entry()
                    message = order._l10n_br_edi_get_successful_message(adjustment_move)

                    order.l10n_br_avatax_error = False
                    order.l10n_br_last_avatax_status = "accepted"
                    order.l10n_br_access_key = response.get("key")

                    status = response.get("status", {})
                    order.l10n_br_edi_protocol_authorization_number = status.get("protocol")
                    order.l10n_br_edi_authorization_date = status.get("authorizationDateTime")
                    order.l10n_br_edi_series = status.get("serial")

                    order._l10n_br_edi_log_taxes()
                    order.with_context(no_new_invoice=True).message_post(
                        body=message,
                        attachment_ids=order._l10n_br_edi_attachments_from_response(
                            response, save_avalara_pdf=save_avalara_pdf
                        ).ids,
                    )
