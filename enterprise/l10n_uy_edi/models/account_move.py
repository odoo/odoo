import base64
import stdnum.uy
import unicodedata
import logging
from datetime import datetime
from lxml import etree
from markupsafe import Markup

from odoo import _, api, fields, models, Command

from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_repr, float_round, cleanup_xml_node, format_amount, html2plaintext
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)


def format_float(amount, digits=2, valid_zero=None):
    if not amount and not valid_zero:
        return None
    return float_repr(float_round(amount, digits), digits)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_uy_edi_document_id = fields.Many2one("l10n_uy_edi.document", string="Uruguay E-Invoice CFE", copy=False)
    l10n_uy_edi_addenda_ids = fields.Many2many(
        "l10n_uy_edi.addenda",
        string="Addenda & Disclosure",
        domain="[('type', 'in', ['issuer', 'receiver', 'cfe_doc', 'addenda'])]",
        help="Addendas and Mandatory Disclosure to add on the CFE. They can be added either to the issuer, receiver,"
        " or CFE document's additional information section, or to the addenda section. However, the item type should"
        " not be set in this field; instead, it should be specified in the invoice lines.",
        ondelete="restrict")
    l10n_uy_edi_cfe_sale_mode = fields.Selection(
        string="Sales Modality",
        selection=[
            ("1", "General Regime"),
            ("2", "Consignment"),
            ("3", "Reviewable Price"),
            ("4", "Own goods to customs exclaves"),
            ("90", "General Regime - exportation of services"),
            ("91", "Export under Mandate"),
            ("99", "Other transactions"),
        ],
        help="This field is used in the XML to create an Export e-Invoice",
    )
    l10n_uy_edi_cfe_transport_route = fields.Selection(
        string="Transportation Route",
        selection=[
            ("1", "Maritime"),
            ("2", "Air"),
            ("3", "Ground"),
            ("8", "N/A"),
            ("9", "Other"),
        ],
        help="This field is used in the XML to create an Export e-Invoice",
    )

    # Related fields
    l10n_uy_edi_cfe_uuid = fields.Char(related="l10n_uy_edi_document_id.uuid")
    l10n_uy_edi_cfe_state = fields.Selection(related="l10n_uy_edi_document_id.state", store=True)
    l10n_uy_edi_error = fields.Text(related="l10n_uy_edi_document_id.message")
    l10n_uy_edi_journal_type = fields.Selection(related="journal_id.l10n_uy_edi_type")

    # Compute fields
    l10n_uy_edi_is_needed = fields.Boolean(compute="_compute_l10n_uy_edi_is_needed")
    l10n_uy_edi_xml_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Uruguay E-Invoice XML",
        compute="_compute_l10n_uy_edi_xml_attachment_id",
        help="Uruguay: the most recent e-invoice XML returned by UCFE Provider.",
    )

    # Compute method

    def _compute_name(self):
        uy_invoices = self.filtered(
            lambda m: m.l10n_uy_edi_is_needed
            and m.state == "posted"
        )

        super(AccountMove, self - uy_invoices)._compute_name()
        for move in uy_invoices:
            if not move.name or move.name == "/":
                move.name = "* %s" % move.id

    @api.depends("l10n_uy_edi_cfe_state", "country_code", "move_type")
    def _compute_l10n_uy_edi_is_needed(self):
        for move in self:
            move.l10n_uy_edi_is_needed = (
                move.country_code == "UY"
                and move.journal_id.l10n_latam_use_documents
                and move.journal_id.l10n_uy_edi_type == "electronic"
                and move.is_sale_document()
                and (not move.l10n_uy_edi_cfe_state or move.l10n_uy_edi_cfe_state == "error")
            )

    @api.depends("l10n_uy_edi_document_id.state", "move_type")
    def _compute_l10n_uy_edi_xml_attachment_id(self):
        for move in self:
            doc = move.l10n_uy_edi_document_id
            move.l10n_uy_edi_xml_attachment_id = (
                doc.state == "accepted"
                or move.is_sale_document()
            ) and doc.attachment_id

    @api.depends("state", "l10n_uy_edi_document_id.state")
    def _compute_show_reset_to_draft_button(self):
        """ Hide reset to draft button if the edi document has been already processed by DGI """
        # EXTEND from account
        super()._compute_show_reset_to_draft_button()
        for move in self.filtered(
            lambda x: x.country_code == "UY" and x.is_sale_document(include_receipts=True) and x.l10n_uy_edi_document_id
        ):
            move.show_reset_to_draft_button = move.l10n_uy_edi_document_id._can_edit()

    # Constraints method

    @api.constrains("l10n_uy_edi_addenda_ids")
    def _l10n_uy_edi_check_addenda_type_item(self):
        """ avoid letting the user add/create a disclosure of type Product/Service Detail in the Addenda
        and Disclosure field. Product/Service Detail type can only be added in the invoice lines """
        if self.l10n_uy_edi_addenda_ids.filtered(lambda x: x.type == "item"):
            raise ValidationError(_("Product/Service Detail type Disclosure can only be added on invoice lines"))

    # Extend existing methods

    def action_post(self):
        # EXTEND account
        """ If journal configured to auto open the send and print wizard is set then
        will do it. """
        res = super().action_post()
        self.filtered("l10n_uy_edi_error").l10n_uy_edi_document_id.unlink()
        if any(self.journal_id.mapped("l10n_uy_edi_send_print")):
            return self.action_send_and_print()
        return res

    def button_draft(self):
        """ When an invoice sent to DGI returns errors (e.g., wrong partner or other data issues), users can reset it
        to draft and make corrections. However, changing the partner triggers a validation error because the invoice
        lacks a valid latam document number (only provided by DGI after processing). To avoid this, resetting the
        invoice to draft clears the invoice name, allowing users to fix any errors without triggering the validation
        """
        super().button_draft()
        self.filtered(
            lambda x: x.country_code == "UY" and
            x.journal_id.l10n_uy_edi_type == "electronic" and
            x.is_sale_document() and (
                not x.l10n_uy_edi_document_id or
                x.l10n_uy_edi_document_id.state not in ["received", "accepted", "rejected"]
            )
        ).name = False

    def _is_manual_document_number(self):
        # EXTEND l10n_latam_invoice_document
        """ If we have an UY Sales Manual journal then the document number should always be manually add by the user """
        if self.country_code == 'UY' and self.journal_id.type == 'sale' and self.journal_id.l10n_uy_edi_type == 'manual':
            return True
        return super()._is_manual_document_number()

    def _get_last_sequence(self, relaxed=False, with_prefix=None):
        # EXTEND account
        """ l10n_latam_document_number is required in the view if no highest_name is set and so we provide a dummy one,
        so the user does not have to set the document_number.

        :return: string with the sequence, something like "E-ticket 0000001"""
        res = super()._get_last_sequence(relaxed=relaxed, with_prefix=with_prefix)
        if self.country_code == "UY" and not res and self.l10n_uy_edi_is_needed and self.l10n_latam_document_type_id:
            res = "%s 00000000" % self.l10n_latam_document_type_id.doc_code_prefix
        return res

    def _get_l10n_latam_documents_domain(self):
        # EXTEND l10n_latam_invoice_document
        """ Only return the implemented electronic document types so far if the user want to issue from Odoo """
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if (
            self.country_code == "UY"
            and self.journal_id.type == "sale"
            and self.journal_id.l10n_uy_edi_type == "electronic"
        ):
            domain += [('code', 'in', ["101", "102", "103", "111", "112", "113", "121", "122", "123"])]
        return domain

    # Helpers

    def l10n_uy_edi_action_update_dgi_state(self):
        res = self.l10n_uy_edi_document_id.action_update_dgi_state()
        to_cancel = self.filtered(lambda x: x.l10n_uy_edi_cfe_state == 'rejected')
        to_post = self.filtered(lambda x: x.l10n_uy_edi_cfe_state == 'accepted' and x.state == 'cancel')
        if to_cancel:
            try:
                to_cancel._check_fiscal_lock_dates()
                to_cancel.line_ids._check_tax_lock_date()
            except UserError as e:
                _logger.warning(
                    "Cannot cancel rejected invoice(s): %s, error: %s", [(rec.id, rec.name) for rec in to_cancel], str(e)
                )
            else:
                to_cancel.button_draft()
                to_cancel.button_cancel()
                _logger.info(
                    "Cancelled rejected invoice(s): %s", [(rec.id, rec.name) for rec in to_cancel]
                )
                # Send a message to the internal followers or to the Accounting Managers instead
                # prompting manual review and resubmission
                accounting_manager_partners = self.env.ref('account.group_account_manager').users.mapped('partner_id')
                for move in to_cancel:
                    internal_followers = move.message_partner_ids.filtered(
                        lambda x: x.user_ids and not x.user_ids.share)
                    partner_ids = (internal_followers or accounting_manager_partners).ids
                    move.message_post(
                        body=self.env._(
                            'The CFE has been rejected by DGI so we automatically cancel this record. Please, '
                            'you will need to manually check the reject reason and generate/send a new CFE with the fixes'),
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                        partner_ids=partner_ids)
        if to_post:
            to_post.button_draft()
            to_post.action_post()
            _logger.info(
                "Posted previously rejected invoice(s): %s", [(rec.id, rec.name) for rec in to_post]
            )
        return res

    def l10n_uy_edi_action_download_preview_xml(self):
        if self.l10n_uy_edi_document_id.attachment_id:
            return self.l10n_uy_edi_document_id.action_download_file()

    def _l10n_uy_edi_cfe_A_iddoc(self):
        """ XML Section A (Encabezado) """

        if self.invoice_line_ids.product_id.filtered(lambda x: x.type in ("consu", "product")):
            incoterm = self.invoice_incoterm_id.code
        else:
            incoterm = "N/A"
            self.l10n_uy_edi_cfe_transport_route = "8"

        return {
            "FchEmis": fields.Date.to_string(self.date),  # A5
            "MntBruto":  # A10 - Tax Included
                1 if self.line_ids.tax_ids.filtered(lambda x: x.l10n_uy_tax_category == "vat" and x.price_include)
                else None,
            "FmaPago":  # A11: (1 cash, 2 credit). If the payment date is same as invoice date, and payment term only
                # have one line then is cash, if not then credit
                2 if self.invoice_date_due > self.invoice_date or len(self.invoice_payment_term_id.line_ids) > 1
                else 1,
            "FchVenc": fields.Date.to_string(self.invoice_date_due),  # A12
            "ClauVenta": self._l10n_uy_edi_is_expo_cfe() and incoterm or None,  # A13
            "ModVenta": self._l10n_uy_edi_is_expo_cfe() and self.l10n_uy_edi_cfe_sale_mode or None,  # A14
            "ViaTransp": self._l10n_uy_edi_is_expo_cfe() and self.l10n_uy_edi_cfe_transport_route or None,  # A15
            "InfoAdicionalDoc": self.l10n_uy_edi_document_id._get_legends("cfe_doc", self) or None,  # A16
        }

    def _l10n_uy_edi_cfe_A_issuer(self):
        """ XML Section A (Encabezado / Emisor) """
        self.ensure_one()
        edi_doc = self.l10n_uy_edi_document_id
        return {
            "RUCEmisor": stdnum.uy.rut.compact(self.company_id.vat),  # A40
            "RznSoc": self.company_id.name[:150],  # A41
            "CdgDGISucur": self.company_id.l10n_uy_edi_branch_code,  # A47
            "DomFiscal": self.company_id.partner_id._l10n_uy_edi_get_fiscal_address(),  # A48
            "Ciudad": self.company_id.city[:30],  # A49
            "Departamento": self.company_id.state_id.name[:30],  # A50
            "InfoAdicionalEmisor": edi_doc._get_legends("issuer", self) or None,  # A51
        }

    def _l10n_uy_edi_cfe_A_receptor(self):
        """ XML Section A (Encabezado / Receptor) """
        self.ensure_one()
        receptor_required = self.l10n_uy_edi_document_id._cfe_needs_partner_info(self)

        # If we do not have the necessary receiver information, but the receiver information is not required,
        # we will not send it.
        if not self.partner_id.vat and not receptor_required:
            return {}

        doc_type = self.partner_id._l10n_uy_edi_get_doc_type()

        # If we have the information available about the receiver, we send it no matter the case
        # (this is what Uruware does)
        return {
            "TipoDocRecep": doc_type or None,  # A60
            "CodPaisRecep": self.partner_id.country_id.code or ("UY" if doc_type in [2, 3] else "99"),  # A61
            "DocRecep": self.commercial_partner_id.vat if doc_type in [1, 2, 3] else None,  # A62
            "DocRecepExt": self.commercial_partner_id.vat if doc_type not in [1, 2, 3] else None,  # A62.1
            "RznSocRecep": self.commercial_partner_id.name[:150] or None,  # A63
            "DirRecep": self.partner_id._l10n_uy_edi_get_fiscal_address() or None,  # A64
            "CiudadRecep": self.partner_id.city and self.partner_id.city[:30] or None,  # A65
            "DeptoRecep": self.partner_id.state_id and self.partner_id.state_id.name[:30] or None,  # A66
            "PaisRecep": self.partner_id.country_id and self.partner_id.country_id.name or None,  # A66.1
            "InfoAdicional": self.l10n_uy_edi_document_id._get_legends("receiver", self) or None,  # A68
            "CompraID": self.ref and self.ref[:50] or None,  # A70
        }

    def _l10n_uy_edi_cfe_B_details(self, tax_details):
        """ XML Section B (Detalle de Productos y Servicios)

        Check the restriction on the maximum number of lines that we can report, launch a prior exception from Odoo
        to avoid sending and receiving a rejection by DGI if we do not meet the specification.

        :return:  list of the prepare data of each line we are going to inform for the CFE """
        self.ensure_one()
        res = []

        # NOTE: all amounts to be reported must be in the currency of the receipt not in Uruguayan pesos,
        # that is why we use price_subtotal instead of another field

        k = 1
        for base_line in tax_details['base_lines']:
            line = base_line['record']
            if line.price_unit < 0:
                continue

            tax_info = tax_details['tax_details_per_record'][line]['tax_details'].values()
            values = next(iter(tax_info)) if tax_info else False
            tax_included = values['_tax_price_include'] if tax_info else False

            invoice_ind = self._get_invoice_indicator(line, tax_details)

            nom_item, item_description = self._l10n_uy_edi_get_line_nom_and_desc(line)
            temp = {
                "NroLinDet": k,  # B1
                "IndFact": invoice_ind,  # B4
                "NomItem": nom_item,  # B7
                "DscItem": item_description if item_description else None,  # B8
                "Cantidad": abs(line.quantity) if invoice_ind == 7 else line.quantity,  # B9
                "UniMed": line.product_uom_id.name[:4] if line.product_uom_id else "N/A",  # B10
                "PrecioUnitario": line.price_unit,  # B11
                "DescuentoPct": line.discount,  # B12
                "DescuentoMonto":  # B13
                (abs(line.quantity) * line.price_unit - (line.price_total if tax_included else line.price_subtotal))
                if line.discount else None,
                "MontoItem": abs(line.price_total) if tax_included else abs(line.price_subtotal),  # B24
            }

            if invoice_ind == 5:
                temp.update({}.fromkeys(['PrecioUnitario', 'DescuentoMonto', 'DescuentoPct'], 0.0))

            res.append(temp)
            k += 1
        return res

    def _l10n_uy_edi_cfe_C_totals(self, tax_details):
        """ XML Section C (SUBTOTALES INFORMATIVOS) """
        self.ensure_one()
        currency_name = self.currency_id.name if self.currency_id else self.company_id.currency_id.name

        expo_doc = self._l10n_uy_edi_is_expo_cfe()

        neto = {10.0: 0.0, 22.0: 0.0, 0.0: 0.0}
        base = neto.copy()
        neto_keys = neto.keys()

        for grouping_key, tax_dict in tax_details['tax_details'].items():
            key = grouping_key['_tax_amount'] if grouping_key['_tax_amount'] in neto_keys else 'reduced_tax'
            neto[key] = neto.get(key, 0) + tax_dict['base_amount_currency']
            base[key] = base.get(key, 0) + tax_dict['tax_amount_currency']
        nf_amount = sum(
            self.invoice_line_ids.filtered(lambda x: x.move_id._is_downpayment() or x.quantity < 0).mapped('price_subtotal')
        )
        res = {
            "TpoMoneda": currency_name,  # A110
            "TpoCambio": None if currency_name == "UYU" else self._l10n_uy_edi_get_used_rate(),  # A111
            "MntExpoyAsim": self.amount_total if expo_doc else None,  # A113
            "MntNoGrv": neto[0.0] if not expo_doc else None,  # A112
            "MntNetoIvaTasaMin": neto[10.0] if not expo_doc else None,  # A116
            "IVATasaMin": 10 if not expo_doc and neto[10.0] or self._is_downpayment() else None,  # A119
            "MntNetoIVATasaBasica": neto[22.0] if not expo_doc else None,  # A117
            "MntNetoIVAOtra": neto.get('reduced_tax'),  # A118
            "IVATasaBasica": 22 if not expo_doc and neto[22.0] or self._is_downpayment() else None,  # A120
            "MntIVATasaMin": base[10.0] if not expo_doc else None,  # A121
            "MntIVATasaBasica": base[22.0] if not expo_doc else None,  # A122
            "MntIVAOtra": base.get('reduced_tax'),  # A123
            "MntTotal": self.amount_total - nf_amount if nf_amount else self.amount_total,  # A124
            "CantLinDet": len(self.invoice_line_ids.filtered(lambda x: x.display_type == "product" and x.price_unit >= 0 or x.move_id._is_downpayment())),  # A126
            "MontoNF": nf_amount or None,
            "MntPagar": self.amount_total,  # A130
        }
        return res

    def _l10n_uy_edi_cfe_D_global_discount(self, tax_details):
        """XML Section D (Descuntos y recargos)
        Filter global discount lines. This section is used to specify discounts or surcharges that apply to the total
        document amount, without the need to detail them item by item.
        :return:  list of the prepare data of each line we are going to inform for the CFE """
        self.ensure_one()
        res = []
        for k, line in enumerate(self.invoice_line_ids.filtered(lambda line: line.price_unit < 0), 1):

            invoice_ind = self._get_invoice_indicator(line, tax_details)

            res.append({
                "NroLinDR": k,  # D1
                "TpoMovDR": "D",  # D2
                "TpoDR": 1,  # D3
                "GlosaDR": line.name[:100] if line.name else _('Discount'),  # D5
                "ValorDR": abs(line.price_unit),  # D6
                "IndFactDR": invoice_ind,  # D7
            })

        return res

    def _l10n_uy_edi_cfe_F_reference(self):
        """ XML Section F (REFERENCE INFORMATION). If is a debit/credit note cfe then we need to inform the reference tag """
        res = []
        if self.l10n_latam_document_type_id.internal_type in ["credit_note", "debit_note"]:
            related_doc = self._l10n_uy_edi_found_related_cfe()
            for k, related_cfe in enumerate(related_doc, 1):
                cfe_serie, cfe_number = self.l10n_uy_edi_document_id._get_doc_parts(related_cfe)
                res.append({
                    "NroLinRef": k,  # F1
                    "TpoDocRef": int(related_cfe.l10n_latam_document_type_id.code),  # F3
                    "Serie": cfe_serie,  # F4
                    "NroCFERef": cfe_number,  # F5
                    "FechaCFEref": related_cfe.invoice_date,  # F7
                    "MntCFEref": related_cfe.amount_total,  # F8
                    "TpoMonedaRef": related_cfe.currency_id.name,  # F9
                    "TpoCambioRef": related_cfe._l10n_uy_edi_get_used_rate(),  # F10
                })
        return res

    def _get_invoice_indicator(self, line, tax_details):
        # B4 IndFact
        if self._l10n_uy_edi_is_expo_cfe():
            invoice_ind = 10  # Exportación y asimiladas
        elif self._is_downpayment():
            invoice_ind = 6
        elif line.quantity < 0:
            invoice_ind = 7  # Discount
        else:
            ind_code = {
                0.0: 1,   # 1: Exento de IVA
                10.0: 2,  # 2: Gravado a Tasa Mínima
                22.0: 3,  # 3: Gravado a Tasa Básica
            }
            # IMPORTANT: By the moment, this is working for one VAT tax per move lines
            invoice_ind = ind_code.get(line.tax_ids.amount, 4)  # 4: Otra Tasa IVA

        tax_included = set(line.tax_ids.mapped("price_include"))

        # We made this in separate if because expo invoices can also have entrega gratuita
        if line.currency_id.is_zero(line.price_total if tax_included else line.price_subtotal):
            invoice_ind = 5  # Entrega Gratuita

        return invoice_ind

    def _l10n_uy_edi_check_move(self):
        """ Need to fullfil next conditions:

        * Check receiver has a valid identification number
        * Check that we do not sent any tax on exportation invoices
        * Check that domestic CFE always has a vat tax per line
        * Check that Doc type is set and is a valid one
        * Check that the Partner address info is set if required for the doc type
        * Check if discounts with X tax then should be another line not discount that share the same tax

        return: an error list if the minimal conditions to be a valid CFE does not fulfill """
        self.ensure_one()
        errors = []
        if not (self.company_id.country_code == "UY" and self.l10n_latam_use_documents):
            return errors

        edi_model = self.env["l10n_uy_edi.document"]

        # Check Issuer data
        if config_errors := self.company_id._l10n_uy_edi_validate_company_data():
            errors.append(_(
                "To create the CFE document first complete your company data (%(company_name)s):\n\t- %(errors)s",
                errors="\n\t- ".join(config_errors),
                company_name=self.company_id.name))

        # Check receiver has a valid identification number
        try:
            self.partner_id.check_vat()
        except ValidationError as exp:
            errors.append(_("Problem with Receiver identification number: %(exp_msg)s", exp_msg=str(exp)))

        # Check currency configuration works to be able to report to DGI
        uy_edi_currencies = [
            # partial iso 4217
            "ARS", "BRL", "CAD", "CLP", "CNY", "COP", "EUR", "JPY", "MXN", "PYG", "PEN", "USD", "UYU", "VEF",
            # other_currencies
            "UYI", "UYR",
        ]
        currency_names = self.currency_id.mapped("name") + self.company_id.currency_id.mapped("name")
        for currency_name in currency_names:
            if currency_name not in uy_edi_currencies:
                errors.append(_("The currency does not exist on DGI currencies table %s", currency_name))

        # Rates Configuration
        if self.currency_id and self.currency_id.name != "UYU":
            used_rate = self._l10n_uy_edi_get_used_rate()
            if used_rate <= 0.0:
                errors.append(_(
                    "Not valid Currency Rate, need to be greater than 0 to be accepted by DGI"
                    " (%(used_rate)s)", used_rate=used_rate)
                )

        # If debit or credit, we need to ensure that the original related document exists and is accepted by DGI
        if self.l10n_latam_document_type_id.internal_type in ["credit_note", "debit_note"]:
            related_doc = self._l10n_uy_edi_found_related_cfe()
            if not related_doc:
                errors.append(_("To validate a DN/CN the original document should be informed"))
            if not int(related_doc.l10n_latam_document_type_id.code):
                errors.append(_("To validate a DN/CN the original document should be informed and it should be electronic"))

        # For e-Ticket and related DN/CN max lines <= 700
        lines = self.invoice_line_ids.filtered(lambda x: x.display_type not in ("line_section", "line_note"))
        if self.l10n_latam_document_type_id.code in [101, 102, 103, 131, 132, 133] and len(lines) > 700:
            errors.append(_("For e-Ticket and related DN and CN you can only report up to 700 lines"))
        elif len(lines) > 200:  # Other CFE types: Max 200
            errors.append(_("For this type of CFE you can only report up to 200 lines"))

        # We check that not other taxes are being used (not supported for EDI)
        if not_supported_taxes := lines.tax_ids.filtered(lambda x: x.l10n_uy_tax_category != "vat"):
            errors.append(_(
                "Not valid Uruguayan tax, only VAT taxes are supported (%(taxes_name)s)",
                taxes_name=', '.join(not_supported_taxes.mapped('name'))),
            )

        # Check expo conditions
        expo_doc = int(self.l10n_latam_document_type_id.code) in [121, 122, 123]
        # Where: 121 "Export e-Invoice" / 122 "Export e-Invoice Credit Note" / 123 "Export e-Invoice Debit Note"
        # Ensure required fields for expo invoices
        if expo_doc:
            missing_expo_fields = []
            has_products = self.invoice_line_ids.product_id.filtered(lambda x: x.type in ("consu", "product"))
            if has_products and not self.invoice_incoterm_id:
                missing_expo_fields.append("Incoterm")
            if not self.l10n_uy_edi_cfe_sale_mode:
                missing_expo_fields.append("Sales Modality")
            if has_products and not self.l10n_uy_edi_cfe_transport_route:
                missing_expo_fields.append("Transportation Route")

            if missing_expo_fields:
                errors.append(_(
                    "To report an export invoice you must fill the next fields. "
                    "You can indicate this value in the Other Information tab: "
                    " \n\t * %s", "\n\t * ".join(missing_expo_fields)))

        # Check lines
        # When I create an invoice with Anticipo directly, the line is not downpayment so we have an error -
        # All lines should have a VAT tax -
        for line in lines.filtered(lambda x: not x.move_id._is_downpayment() and x.quantity > 0):
            errors += edi_model._check_field_size("B8_DscItem", self._l10n_uy_edi_get_line_nom_and_desc(line)[1], 1000)
            # We check that there is one and o nly one vat tax per line
            vat_taxes = line.tax_ids.filtered(lambda x: x.l10n_uy_tax_category == "vat")
            if len(vat_taxes) != 1:
                errors.append(_(
                    "All lines should have a VAT tax (only one per line). "
                    "Check line '%(line_name)s' (Id Invoice: %(move_id)s)",
                    line_name=line.product_id.name or line.name,
                    move_id=line.move_id.id,
                ))
            elif expo_doc:
                if line.tax_ids.amount != 0.0:
                    errors.append(_(
                        "Export CFE can only have 0%% vat taxes. Check line '%(line_name)s' (Id Invoice: %(move_id)s)",
                        line_name=line.product_id.name,
                        move_id=line.move_id.id,
                    ))

        # Check the type of vat taxes used (all included or not included)
        taxes = self.line_ids.tax_ids.filtered(lambda t: t.l10n_uy_tax_category == "vat")
        tax_included = set(taxes.mapped("price_include"))
        if tax_included and len(tax_included) != 1:
            errors.append(_("You cannot combine included and not included taxes on the same invoice"))

        # Downpayments invoices or deduct downlapyment lines should not have taxes
        if self._is_downpayment() and self.invoice_line_ids.tax_ids:
            errors.append(_("Downpayment invoices should not have any taxes, please remove any taxes from"
                            " the downpayment line to continue."))
        deduct_dp_lines = self.invoice_line_ids.filtered(lambda l: l.quantity < 0 and l._get_downpayment_lines())
        if deduct_dp_lines.filtered(lambda l: l.tax_ids):
            errors.append(_("Downpayment lines should not have any taxes, please remove then to continue"))

        # Discount line have regular lines that match with the same tax
        total_field = 'price_total' if tax_included else 'price_subtotal'
        discount_lines = (self.invoice_line_ids - deduct_dp_lines).filtered(lambda l: l[total_field] < 0.0)
        for dline in discount_lines:
            discount_tax = dline.tax_ids
            if not self.line_ids.filtered(lambda l: l.id != dline.id).\
               tax_ids.filtered(lambda t: t.id == discount_tax.id):
                errors.append(_('Discount with Tax %s can only exist if match with regular line with same tax',
                                discount_tax.name))

        # Do not let negative quantities, only can be done if line is a donwpayment deduct
        negative_lines = self.line_ids.filtered(lambda l: l.quantity < 0 and not l._get_downpayment_lines())
        if negative_lines:
            errors.append(_("You cannot create lines with negative quantities (except for down payments deducts)."))

        # Check the receiver info depending on the doc type
        edi_model = self.env["l10n_uy_edi.document"]
        document_type = int(self.l10n_latam_document_type_id.code)
        cond_e_fact = document_type in [111, 112, 113, 141, 142, 143]
        # Where:
        # 111 e-Invoice
        # 112 e-Invoice Credit Note
        # 113 e-Invoice Debit Note
        # 141 e-Invoice Sale By Third Party
        # 142 e-Invoice Sale By Third Party Credit Note
        # 143 e-Invoice Sale By Third Party Debit Note
        cond_e_ticket = document_type in [101, 102, 103, 131, 132, 133]
        # Where:
        # 101 e-Ticket
        # 102 e-Ticket Credit Note
        # 103 e-Ticket Debit Note
        # 131 e-Ticket Sale By Third Party
        # 132 e-Ticket Sale By Third Party Credit Note
        # 133 e-Ticket Sale By Third Party Debit Note

        cond_e_fact_expo = self._l10n_uy_edi_is_expo_cfe()
        receptor_required = edi_model._cfe_needs_partner_info(self)
        doc_type = self.partner_id._l10n_uy_edi_get_doc_type()
        min_amount = edi_model._get_minimum_legal_amount(self.company_id, self.date)

        if min_amount == 1.0:
            errors.append(_("You need to have UYI rate before validating invoices"))

        if not doc_type:
            errors.append(_("%(dtype)s is not an Uruguayan Identification Type or "
                            "a Generic one (VAT, Passport, or Foreign ID). You need to select a valid ID to be able "
                            "to invoice", dtype=self.partner_id.l10n_latam_identification_type_id.name))

        # Validations to have all the receiver data if the receiver is required
        if receptor_required:
            if not self.partner_id.l10n_latam_identification_type_id:
                errors.append(_("The partner of the CFE needs to have an Identification Type"))

        if cond_e_fact_expo or cond_e_fact or (cond_e_ticket and receptor_required):
            if not all([self.partner_id.street, self.partner_id.city, self.partner_id.state_id,
                        self.partner_id.country_id, self.partner_id.vat]):
                msg = _("You need to fill in the receiver details: address, city, province, country and ID number")
                if cond_e_ticket:
                    msg += _(
                        "\n\nNOTE: This is required since the e-Ticket exceeds the minimum amount."
                        "\nMinimum amount = 5000 Uruguayan Indexed Unit (>%(min_amount)s)",
                        min_amount=format_amount(self.env, min_amount, self.company_currency_id),
                    )
                errors.append(msg)

        # Check field length of special tags that have mandatory disclosure included and warn the user if the text
        # length is more that the MAX (this way we avoid that mandatory disclosure can result incomplete on the XML,
        # we need this validation because the mandatory disclosure have legal implication, and we need to ensure
        # that all the needed text is in the CFE)
        errors += edi_model._check_field_size(
            "A51_InfoAdicionalEmisor", edi_model._get_legends("issuer", self) or None, 150)
        errors += edi_model._check_field_size(
            "A16_InfoAdicionalDoc", edi_model._get_legends("cfe_doc", self) or None, 150)
        errors += edi_model._check_field_size(
            "A68_InfoAdicional", edi_model._get_legends("receiver", self) or None, 150)

        # Check that the document type has been implemented, if not do not let the user create the doc
        if not edi_model._get_cfe_tag(self):
            errors.append(_("This CFE is not implemented yet %(doc_name)s", doc_name=self.l10n_latam_document_type_id.display_name))

        # If found related document then it should be electronic one (should have serie and number)
        if related_cfe := self._l10n_uy_edi_found_related_cfe():
            cfe_serie, cfe_number = self.l10n_uy_edi_document_id._get_doc_parts(related_cfe)
            if not cfe_serie or not cfe_number:
                errors.append(_("The related CFE (%s) should be electronic", related_cfe.name))

        return errors

    def _l10n_uy_edi_cron_update_dgi_status(self, batch_size=10):
        res = self.search([("l10n_uy_edi_cfe_state", "=", "received"), ("journal_id.type", "=", "sale")])
        res[:batch_size].l10n_uy_edi_action_update_dgi_state()
        if len(res) > batch_size:
            self.env.ref("l10n_uy_edi.ir_cron_update_dgi_state")._trigger()

    def _l10n_uy_edi_dummy_validation(self):
        """ When we want to skip DGI and validate only in Odoo """
        self.l10n_uy_edi_document_id.state = "accepted"
        self.write({
            "l10n_latam_document_number": "DE%07d" % self.id,
            "ref": "*DEMO",
        })
        return self._l10n_uy_edi_get_preview_xml()

    def _l10n_uy_edi_found_related_cfe(self):
        """ Return the related/origin CFE of a given CFE. """
        self.ensure_one()
        res = self.env["account.move"]
        if self.l10n_latam_document_type_id.internal_type == "credit_note":
            res = self.reversed_entry_id
        elif self.l10n_latam_document_type_id.internal_type == "debit_note":
            res = self.debit_origin_id
        if res:
            if res.l10n_uy_edi_cfe_state != "accepted":
                res.l10n_uy_edi_document_id.action_update_dgi_state()
        return res

    def _l10n_uy_edi_get_addenda(self):
        """ return string with the addenda """
        addenda = self.l10n_uy_edi_document_id._get_legends("addenda", self)
        if self.narration:
            term_and_conditions = html2plaintext(self.narration)
            addenda = addenda + "\n\n" + term_and_conditions if addenda else term_and_conditions
        return self._l10n_uy_edi_clean_non_ascii_chars(addenda)

    def _l10n_uy_edi_clean_non_ascii_chars(self, text):
        """Deletes non-ASCII characters from strings."""
        if isinstance(text, str):
            return ''.join(char for char in text if (ord(char) <= 127) or unicodedata.category(char) == 'Ll' or unicodedata.category(char) == 'Lu')
        return text

    def _l10n_uy_edi_get_line_nom_and_desc(self, aml):
        """
        Generate the item name and description for a given account move line (aml).

        This method extracts and formats the name and description of a product or
        account move line based on the provided data. It handles cases where the
        product is not defined, includes multilingual support, and appends additional
        information from addenda if present.
        Returns a tuple containing:
                - nom_item (str): The formatted name of the item (up to 80 characters).
                - description (str): The description of the item, including any
                  additional addenda content if applicable.
        """
        # B7 NomItem, B8 DscItem
        # NomItem is a mandatory field, so if there is no product_id, we use
        # the description of the line (aml.name).
        if not aml.product_id:
            nom_item = aml.name and aml.name[:80] or '-'
            description = aml.name and aml.name[80:] or ''
        else:
            # If the product is defined, we use its name as the item name
            # and the line name as the description.
            display_name = aml.with_context(lang=aml.partner_id.lang).product_id.display_name \
                if aml.partner_id.lang else aml.product_id.display_name
            nom_item = display_name[:80]

            # The description has the product name, so we do not include that part
            description = display_name[80:]
            if aml.name:
                description += aml.name.replace(display_name, '').replace('\n', '')

        if aml.l10n_uy_edi_addenda_ids:
            adenda = [" {%s}" % addenda.content if addenda.is_legend else " " + addenda.content for addenda in aml.l10n_uy_edi_addenda_ids]
            description += str(*adenda)

        return nom_item, description

    def _l10n_uy_edi_get_pdf(self):
        """ Call endpoint to get PDF file from Uruware (Standard Representation)
        return: dictionary with {"errors": str(): "pdf_file"attachment object } """
        res = {}
        if "out" not in self.move_type or self.journal_id.l10n_uy_edi_type != "electronic":
            return {"errors": _("Only can get the legal representation of the CFE for customer electronic invoices")}

        result = self.l10n_uy_edi_document_id._get_pdf()

        if file_content := result.get("file_content"):
            pdf_file = self.env["ir.attachment"].create({
                "res_model": "account.move",
                "res_id": self.id,
                "res_field": "invoice_pdf_report_file",
                "name": (self.name or _("INV")).replace("/", "_") + ".pdf",
                "type": "binary",
                "datas": file_content,
            })
            res["pdf_file"] = pdf_file

        return res

    def _l10n_uy_edi_get_preview_xml(self):
        self.ensure_one()
        edi_doc = self.l10n_uy_edi_document_id
        edi_doc.attachment_id.res_field = False
        xml_file = self.env["ir.attachment"].create({
            "res_model": "l10n_uy_edi.document",
            "res_field": "attachment_file",
            "res_id": edi_doc.id,
            "name": edi_doc._get_xml_attachment_name(),
            "type": "binary",
            "datas": base64.b64encode(self._l10n_uy_edi_get_xml_content().encode()),
        })
        edi_doc.invalidate_recordset(["attachment_id", "attachment_file"])
        return xml_file

    def _l10n_uy_edi_get_used_rate(self):
        self.ensure_one()
        UYU = self.env.ref("base.UYU")
        res = 0.0
        if self.currency_id != UYU:
            res = self.currency_id._convert(
                1.0, UYU, self.company_id, self.date or fields.Date.today(), round=False)
        return res

    def _l10n_uy_edi_get_xml_content(self):
        """ Create the CFE xml structure and validate it
            :return: string the xml content to send to DGI """
        self.ensure_one()

        def grouping_key_generator(base_line, tax_data):
            tax = tax_data['tax']
            return {
                'l10n_uy_tax_category': tax.l10n_uy_tax_category,
                '_tax_amount': tax.amount,
                '_tax_price_include': tax.price_include,
            }

        tax_details = self._prepare_invoice_aggregated_taxes(grouping_key_generator=grouping_key_generator)
        template_name = "l10n_uy_edi." + self.l10n_uy_edi_document_id._get_cfe_tag(self) + "_template"
        cfe = self.env["ir.qweb"]._render(template_name, values={
            "cfe": self,
            "IdDoc": self._l10n_uy_edi_cfe_A_iddoc(),
            "emisor": self._l10n_uy_edi_cfe_A_issuer(),
            "receptor": self._l10n_uy_edi_cfe_A_receptor(),
            "item_detail": self._l10n_uy_edi_cfe_B_details(tax_details),
            "totals_detail": self._l10n_uy_edi_cfe_C_totals(tax_details),
            "global_discounts": self._l10n_uy_edi_cfe_D_global_discount(tax_details),
            "referencia_lines": self._l10n_uy_edi_cfe_F_reference(),
            "format_float": format_float,
        })
        return etree.tostring(cleanup_xml_node(cfe)).decode()

    def _l10n_uy_edi_is_expo_cfe(self):
        """ True of False if the CFE is an Export type """
        self.ensure_one()
        return int(self.l10n_latam_document_type_id.code) in [121, 122, 123]

    def _l10n_uy_edi_prepare_req_data(self):
        """ Creating dictionary with the request to generate a DGI EDI document """
        self.ensure_one()
        edi_doc = self.l10n_uy_edi_document_id
        xml_content = self._l10n_uy_edi_get_xml_content()
        req_data = {
            "Uuid": edi_doc.uuid,
            "TipoCfe": int(self.l10n_latam_document_type_id.code),
            "HoraReq": edi_doc.request_datetime.strftime("%H%M%S"),
            "FechaReq": edi_doc.request_datetime.date().strftime("%Y%m%d"),
            "CfeXmlOTexto": xml_content}

        if addenda := self._l10n_uy_edi_get_addenda():
            req_data["Adenda"] = addenda
        return req_data

    def _l10n_uy_edi_send(self):
        """ Create CFE Document and send it to Uruware """
        for move in self:
            move.l10n_uy_edi_document_id.filtered(lambda doc: doc.state == "error").unlink()
            edi_doc = self.env['l10n_uy_edi.document'].create({
                "move_id": move.id,
                "uuid": self.env['l10n_uy_edi.document']._get_uuid(move),
            })
            move.l10n_uy_edi_document_id = edi_doc

            if move.company_id.l10n_uy_edi_ucfe_env == "demo":
                attachments = move._l10n_uy_edi_dummy_validation()
                msg = _("This CFE has been generated in DEMO Mode. It is considered as accepted and it won\"t be sent to DGI.")
            else:
                request_data = move._l10n_uy_edi_prepare_req_data()
                result = edi_doc._send_dgi(request_data)
                edi_doc._update_cfe_state(result)

                response = result.get("response")

                if edi_doc.message:
                    move.message_post(
                        body=Markup("<font style='color:Tomato;'><strong>{}:</strong></font> <i>{}</<i>").format(("ERROR"), edi_doc.message)
                    )
                elif edi_doc.state in ["received", "accepted"]:
                    # If everything is ok we save the return information
                    move.l10n_latam_document_number = \
                        response.findtext(".//{*}Serie") + "%07d" % int(
                            response.findtext(".//{*}NumeroCfe"))

                    msg = response.findtext(".//{*}MensajeRta", "")
                    msg += _("The electronic invoice was created successfully")

                if response is not None:
                    attachments = move._l10n_uy_edi_update_xml_and_pdf_file(response)

            if edi_doc.state in ["received", "accepted", "rejected"]:
                move.with_context(no_new_invoice=True).message_post(
                    body=msg,
                    attachment_ids=attachments.ids if attachments else False,
                )

    def _l10n_uy_edi_update_xml_and_pdf_file(self, response):
        """ Clean up the pdf and xml fields. Create new ones with the response """
        self.ensure_one()
        res_files = self.env["ir.attachment"]
        edi_doc = self.l10n_uy_edi_document_id

        self.invoice_pdf_report_id.res_field = False
        edi_doc.attachment_id.res_field = False

        xml_content = response.findtext(".//{*}XmlCfeFirmado")
        if xml_content:
            res_files = self.env["ir.attachment"].create({
                "res_model": "l10n_uy_edi.document",
                "res_field": "attachment_file",
                "res_id": edi_doc.id,
                "name": edi_doc._get_xml_attachment_name(),
                "type": "binary",
                "datas": base64.b64encode(
                    xml_content.encode() if self.l10n_uy_edi_cfe_state in ["received", "accepted"]
                    else self._l10n_uy_edi_get_xml_content().encode()
                ),
            })

            edi_doc.invalidate_recordset(["attachment_id", "attachment_file"])

            # If the record has been posted automatically print and attach the legal report to the record.
            if self.l10n_uy_edi_cfe_state and self.l10n_uy_edi_cfe_state != "error":
                pdf_result = self._l10n_uy_edi_get_pdf()
                if pdf_file := pdf_result.get("pdf_file"):
                    # make sure latest PDF shows to the right of the chatter
                    pdf_file.register_as_main_attachment(force=True)
                    self.invalidate_recordset(fnames=["invoice_pdf_report_id", "invoice_pdf_report_file"])
                    res_files |= pdf_file
                if errors := pdf_result.get("errors"):
                    msg = _("Error getting the PDF file: %s", errors)
                    self.l10n_uy_edi_error = (self.l10n_uy_edi_error or "") + msg
                    self.message_post(body=msg)
        else:
            self._l10n_uy_edi_get_preview_xml()
        return res_files

    def _compute_l10n_latam_document_type(self):
        """
        The following considerations apply for determining document types based on the partner's identification:
        RUT/RUC (Uruguay): Automatically select e-factura.
        Other documents (Example: CI, PAS, NIE, NIFE, etc.): Automatically select e-ticket
        """
        if uy_einvoices := self.filtered(lambda m: m.country_code == 'UY' and
            m.move_type in ('out_invoice', 'out_refund') and
            m.state == 'draft' and
            not m.posted_before and
            m.journal_id.l10n_uy_edi_type == 'electronic' and
            m.partner_id.l10n_latam_identification_type_id == self.env.ref('l10n_uy.it_rut') and
            not m.debit_origin_id):
            uy_einvoices.l10n_latam_document_type_id = self.env.ref('l10n_uy.dc_e_inv')
        super(AccountMove, self - uy_einvoices)._compute_l10n_latam_document_type()

    def _get_edi_decoder(self, file_data, new=False):
        """ Allows users to upload XML files. If there is more than one CFE in the attachment file then there
        will be created one vendor bill for each CFE. """
        # EXTENDS 'account'
        if (
            self.country_code == 'UY'
            and file_data['type'] == 'xml'
            and b"CdgDGISucur>" in file_data['content']
        ):
            xml_tree = file_data['xml_tree']
            cant_cfe_text = xml_tree.findtext('.//{*}CantCFE')
            cant_cfe = int(cant_cfe_text) if cant_cfe_text else 1

            # Only 'sobres' could have more than one cfe
            if cant_cfe > 1:
                cfes_data = xml_tree.findall(".//{*}CFE")
                moves = self
                for item in range(len(cfes_data) - 1):
                    moves |= self.copy({})
                for index, xml_cfe in enumerate(cfes_data):
                    moves[index]._l10n_uy_edi_complete_cfe_from_xml(xml_cfe)
                return
            return self._l10n_uy_edi_complete_cfe_from_xml(xml_tree)
        return super()._get_edi_decoder(file_data, new=new)

    def _l10n_uy_edi_complete_cfe_from_xml(self, xml_tree, l10n_uy_idreq=False):
        """ Here the vendor bills are completed and synchronized through the Uruware notification request or from
        xml uploaded on vendor bill journal on invoicing dashboard. This method will create the attachment with the
        given xml and also will try to get the odoo pdf from Uruware and attach it in the move. If there is a
        difference between the move total amount in Odoo and the move total amount in the XML, then a message is posted
        in the document informing that situation.
        1) Set the move date.
        2) Set the partner, it is created if no partner exists with the same vat in the database.
        3) Set the currency.
        4) Set the move lines.
        5) Set the move due date.
        6) Set the document type.
        7) Set the document number.
        8) Update move DGI state.
        :param move: The account.move record
        :param xml_tree: The xml_tree from the file obtained from the synchronization.
        :param l10n_uy_idreq: the id from the response_600 when the document is
        created by 'UY: Create vendor bills (sync from Uruware)' cron. """
        self.ensure_one()
        latam_document = self._l10n_uy_edi_get_cfe_document_type(xml_tree)
        is_cobranza = xml_tree.findtext('.//{*}IndCobPropia')
        if not latam_document or latam_document.code in ['124', '181', '182', '224', '281', '282'] or is_cobranza:
            latam_document_name = latam_document.name if latam_document else xml_tree.findtext('.//{*}TipoCFE') or xml_tree.findtext('.//{*}TipoCfe') or 'undefined'
            if is_cobranza:
                latam_document_name += " (Cobranza)"
            msg = _("For now it is not possible to create %(latam_document_name)s documents",
                    latam_document_name=latam_document_name)
            self.message_post(body=msg)
            return
        errors = []
        partner_vat_RUC = xml_tree.findtext(".//{*}RUCEmisor")
        date_format = "%Y-%m-%d"
        # Currency and select/create partner.
        currency = self.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', xml_tree.findtext(".//{*}TpoMoneda"))],
            limit=1
        )
        # Create partner if does not exists.
        doc_number = xml_tree.findtext(".//{*}Serie") + (xml_tree.findtext(".//{*}NumeroCfe") or xml_tree.findtext(".//{*}Nro")).zfill(7)
        if not self.l10n_uy_edi_document_id:  # This means that the XML was dragged and dropped
            self.l10n_uy_edi_document_id._create_edi_move(
                xml_tree,
                move=self,
                company=self.company_id,
                doc_type=latam_document,
                l10n_uy_idreq=str(self.id) + '-manual'
            )
            self.env["ir.attachment"].create({
                "name": f"CFE_{doc_number}_manual.xml",
                "res_model": "l10n_uy_edi.document",
                "res_id": self.l10n_uy_edi_document_id.id,
                "res_field": "attachment_file",
                "type": "binary",
                "datas": base64.b64encode(etree.tostring(xml_tree))})
        self.partner_id = self.l10n_uy_edi_document_id._get_partner_from_xml(xml_tree, partner_vat_RUC)
        self.move_type = latam_document._l10n_uy_edi_get_move_type()
        self.l10n_latam_document_type_id = latam_document
        self.l10n_latam_document_number = doc_number
        self.currency_id = currency
        self.invoice_date = datetime.strptime(xml_tree.findtext(".//{*}FchEmis"), date_format).date()
        serie, number = self.l10n_uy_edi_document_id._get_doc_parts(self)
        self.l10n_uy_edi_document_id._create_pdf_vendor_bill(self, req_data_pdf={
            "rut": self.company_id.vat,
            "rutRecibido": partner_vat_RUC,
            "tipoCfe": self.l10n_latam_document_type_id.code,
            "serieCfe": serie,
            "numeroCfe": number
        })
        try:
            self.line_ids = self._l10n_uy_edi_vendor_prepare_lines(
                line_nodes=xml_tree.findall(".//{*}Item"),
                tax_included=xml_tree.findtext(".//{*}MntBruto") == '1',
                global_discounts_surcharges=xml_tree.findall(".//{*}DRG_Item"),
            )
        except Exception as e:  # noqa: BLE001
            self.invoice_line_ids = False
            self.l10n_latam_document_type_id = latam_document
            self.l10n_latam_document_number = doc_number
            errors.append(str(e))
        if fecha_vto := xml_tree.findtext(".//{*}FchVenc"):
            self.invoice_date_due = datetime.strptime(fecha_vto, date_format).date()
        self.l10n_uy_edi_action_update_dgi_state()
        # Validation of the move total amounts
        amount_total = self.amount_total
        if xml_tree.findtext(".//{*}MntPagar"):
            formatted_xml_amount_total = float(xml_tree.findtext(".//{*}MntPagar"))
            if not self.currency_id.is_zero(amount_total - formatted_xml_amount_total):
                formatted_amount_total = formatLang(self.env, formatted_xml_amount_total, currency_obj=self.currency_id)
                errors.append(_(
                    "There is a difference between the move total amount in Odoo and the move XML. Odoo: %(amount_total)s  XML: %(formatted_amount_total)s.",
                    amount_total=amount_total, formatted_amount_total=formatted_amount_total
                ))
        if errors:
            self.message_post(body="\n - ".join(errors))

    def _l10n_uy_edi_get_cfe_document_type(self, xml_tree):
        """ :return: latam document type in Odoo that represented the XML CFE. """
        # Until now we are not supporting the creation of e-Resguardos and e-Remitos
        l10n_latam_document_type_id = xml_tree.findtext('.//{*}TipoCFE') or xml_tree.findtext('.//{*}TipoCfe')
        return self.env["l10n_latam.document.type"].search([
            ("code", "=", l10n_latam_document_type_id),
            ("country_id.code", "=", "UY"),
        ], limit=1)

    def _l10n_uy_edi_get_tax_not_implemented_description(self, ind_fact):
        """ There are some taxes not implemented for Uruguay, so when move lines are created and if those ones don`t have
        ind_fact (Indicador de facturación) 1, 2 or 3 then is concatenated the name of the tax not implemented with the
        name of the line.  """
        data = {
            "1": "Exento de IVA",
            "2": "Gravado a Tasa Mínima",
            "3": "Gravado a Tasa Básica",
            "4": "Gravado a Otra Tasa/IVA sobre fictos",
            "5": "Entrega gratuita",
            "6": "No facturable",
            "7": "No facturable negativo",
            "8": "Ítem a rebajar en e-remitos",  # Only for e-remitos
            "9": "Ítem a anular en resguardos",  # Only for e-resguardos
            "10": "Exportación y asim",
            "11": "Impuesto percibido",
            "12": "IVA en suspenso",

            # Only for e-Boleta de entrada
            "13": "Ítem vendido por un no contribuyente",
            "14": "Ítem vendido por un contribuyente IVA mínimo, Monotributo o Monotributo MIDES",
            "15": "Ítem vendido por un contribuyente IMEBA",
            "16": "Sólo para ítems vendidos por contribuyentes con obligación IVA mínimo, Monotributo o Monotributo MIDES",
        }

        return data.get(ind_fact, _("UNKNOWN INDICATOR %(ind_fact)s", ind_fact=ind_fact))

    def _l10n_uy_edi_vendor_prepare_lines(self, line_nodes, tax_included, global_discounts_surcharges=False):
        """  Prepare the lines to create vendor bills lines in Odoo from the given xml.
        There are some taxes not implemented for Uruguay, so when line nodes don`t have 10% or 22% or 0% EXEMPT tax then
        is concatenated the name of the tax not implemented with the name of the line.
        :return list of invoice line ids Commands. """
        self.ensure_one()
        invoice_line_ids_commands = []
        # Basic rates: excempt from vat, taxed at minimum rate and taxed at basic rate
        l10n_uy_basic_rates = ["1", "2", "3"]
        for line_node in line_nodes:
            ind_fact = line_node.findtext(".//{*}IndFact")
            domain_tax = self._l10n_uy_edi_get_domain_line_tax(ind_fact, self.company_id, tax_included)
            tax_item = self.env["account.tax"].search(domain_tax, limit=1)
            price_unit = line_node.findtext(".//{*}PrecioUnitario")
            name = line_node.findtext(".//{*}NomItem")
            if ind_fact not in l10n_uy_basic_rates:
                name = f"{name} ({self._l10n_uy_edi_get_tax_not_implemented_description(ind_fact)})"
            tax_ids = [Command.set(tax_item.ids)] if ind_fact in l10n_uy_basic_rates else []
            invoice_line_ids_commands.append(Command.create({
                "name": name,
                "quantity": float(line_node.findtext(".//{*}Cantidad")),
                "price_unit": (1 if ind_fact != "7" else -1) * float(price_unit),
                "tax_ids": tax_ids,
            }))
            if raw_discount_amount := float(line_node.findtext(".//{*}DescuentoMonto", default=False)):
                invoice_line_ids_commands.append(Command.create({
                    "name": name,
                    "quantity": 1,
                    "price_unit": -raw_discount_amount,
                    "tax_ids": tax_ids,
                }))
        for disc_surch in global_discounts_surcharges:
            ind_fact = disc_surch.findtext(".//{*}IndFactDR")
            tax_item = self.env["account.tax"].search(domain_tax, limit=1)
            valor_dr = float(disc_surch.findtext(".//{*}ValorDR"))
            tipo_dr = disc_surch.findtext(".//{*}TpoDR")
            tipo_mov_dr = disc_surch.findtext(".//{*}TpoMovDR")
            if tipo_dr == '1':
                price_unit = valor_dr
            else:
                price_unit = valor_dr * (1 / 100)
            if tipo_mov_dr != 'R':
                price_unit = -price_unit
            invoice_line_ids_commands.append(Command.create({
                "name": disc_surch.findtext(".//{*}GlosaDR"),
                "quantity": 1,
                "price_unit": price_unit,
                "tax_ids": [Command.set(tax_item.ids)] if ind_fact in l10n_uy_basic_rates else []
            }))
        return invoice_line_ids_commands

    def _l10n_uy_edi_get_domain_line_tax(self, ind_fact, company, tax_included=False):
        amount_by_ind = {"1": 0, "2": 10, "3": 22}
        domain_tax = [*self.env['account.tax']._check_company_domain(company), ("country_code", "=", "UY"), ("type_tax_use", "=", "purchase"), ('l10n_uy_tax_category', '=', 'vat')]
        if amount := [('amount', '=', amount_by_ind[ind_fact])] if amount_by_ind.get(ind_fact) is not None else False:
            domain_tax += amount
        if tax_included:
            if company.account_price_include == 'tax_included':
                domain_tax += [("price_include_override", 'in', ('tax_included', 'default'))]
            else:
                domain_tax += [("price_include_override", '=', 'tax_included')]
        return domain_tax
