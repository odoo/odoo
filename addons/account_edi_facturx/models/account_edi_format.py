# -*- coding: utf-8 -*-

from odoo import api, models, fields, tools, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_repr, is_html_empty, str2bool
from odoo.tests.common import Form
from odoo.exceptions import UserError

from datetime import datetime
from lxml import etree
from PyPDF2 import PdfFileReader
import base64
import markupsafe

import io

import logging

_logger = logging.getLogger(__name__)


DEFAULT_FACTURX_DATE_FORMAT = '%Y%m%d'


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _post_invoice_edi(self, invoices):
        self.ensure_one()
        if self.code != 'facturx_1_0_05':
            return super()._post_invoice_edi(invoices)
        res = {}
        for invoice in invoices:
            attachment = self._export_facturx(invoice)
            res[invoice] = {'success': True, 'attachment': attachment}
        return res

    def _is_embedding_to_invoice_pdf_needed(self):
        # OVERRIDE
        self.ensure_one()
        return True if self.code == 'facturx_1_0_05' else super()._is_embedding_to_invoice_pdf_needed()

    def _get_embedding_to_invoice_pdf_values(self, invoice):
        values = super()._get_embedding_to_invoice_pdf_values(invoice)
        if values and self.code == 'facturx_1_0_05':
            values['name'] = 'factur-x.xml'
        return values

    def _prepare_invoice_report(self, pdf_writer, edi_document):
        self.ensure_one()
        if self.code != 'facturx_1_0_05':
            return super()._prepare_invoice_report(pdf_writer, edi_document)
        if not edi_document.attachment_id:
            return

        pdf_writer.embed_odoo_attachment(edi_document.attachment_id, subtype='application/xml')
        if not pdf_writer.is_pdfa and str2bool(self.env['ir.config_parameter'].sudo().get_param('edi.use_pdfa', 'False')):
            try:
                pdf_writer.convert_to_pdfa()
            except Exception as e:
                _logger.exception("Error while converting to PDF/A: %s", e)
            metadata_template = self.env.ref('account_edi_facturx.account_invoice_pdfa_3_facturx_metadata', raise_if_not_found=False)
            if metadata_template:
                pdf_writer.add_file_metadata(metadata_template._render({
                    'title': edi_document.move_id.name,
                    'date': fields.Date.context_today(self),
                }).encode())

    def _export_facturx(self, invoice):

        def format_date(dt):
            # Format the date in the Factur-x standard.
            dt = dt or datetime.now()
            return dt.strftime(DEFAULT_FACTURX_DATE_FORMAT)

        def format_monetary(number, currency):
            # Format the monetary values to avoid trailing decimals (e.g. 90.85000000000001).
            return float_repr(number, currency.decimal_places)

        self.ensure_one()
        # Create file content.
        template_values = {
            **invoice._prepare_edi_vals_to_export(),
            'tax_details': invoice._prepare_edi_tax_details(),
            'format_date': format_date,
            'format_monetary': format_monetary,
            'is_html_empty': is_html_empty,
        }

        xml_content = markupsafe.Markup("<?xml version='1.0' encoding='UTF-8'?>")
        xml_content += self.env.ref('account_edi_facturx.account_invoice_facturx_export')._render(template_values)
        return self.env['ir.attachment'].create({
            'name': 'factur-x.xml',
            'raw': xml_content.encode(),
            'mimetype': 'application/xml'
        })

    def _is_facturx(self, filename, tree):
        return self.code == 'facturx_1_0_05' and tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice'

    def _create_invoice_from_xml_tree(self, filename, tree):
        self.ensure_one()
        if self._is_facturx(filename, tree):
            return self._import_facturx(tree, self.env['account.move'])
        return super()._create_invoice_from_xml_tree(filename, tree)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self._is_facturx(filename, tree):
            return self._import_facturx(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    def _import_facturx(self, tree, invoice):
        """ Decodes a factur-x invoice into an invoice.

        :param tree:    the factur-x tree to decode.
        :param invoice: the invoice to update or an empty recordset.
        :returns:       the invoice where the factur-x data was imported.
        """

        def _find_value(xpath, element=tree):
            return self._find_value(xpath, element, tree.nsmap)

        amount_total_import = None

        default_move_type = False
        if invoice._context.get('default_journal_id'):
            journal = self.env['account.journal'].browse(self.env.context['default_journal_id'])
            default_move_type = 'out_invoice' if journal.type == 'sale' else 'in_invoice'
        elif invoice._context.get('default_move_type'):
            default_move_type = self._context['default_move_type']
        elif invoice.move_type in self.env['account.move'].get_invoice_types(include_receipts=True):
            # in case an attachment is saved on a draft invoice previously created, we might
            # have lost the default value in context but the type was already set
            default_move_type = invoice.move_type

        if not default_move_type:
            raise UserError(_("No information about the journal or the type of invoice is passed"))
        if default_move_type == 'entry':
            return

        # Total amount.
        elements = tree.xpath('//ram:GrandTotalAmount', namespaces=tree.nsmap)
        total_amount = elements and float(elements[0].text) or 0.0

        # Refund type.
        # There is two modes to handle refund in Factur-X:
        # a) type_code == 380 for invoice, type_code == 381 for refund, all positive amounts.
        # b) type_code == 380, negative amounts in case of refund.
        # To handle both, we consider the 'a' mode and switch to 'b' if a negative amount is encountered.
        elements = tree.xpath('//rsm:ExchangedDocument/ram:TypeCode', namespaces=tree.nsmap)
        type_code = elements[0].text

        default_move_type.replace('_refund', '_invoice')
        if type_code == '381':
            default_move_type = 'out_refund' if default_move_type == 'out_invoice' else 'in_refund'
            refund_sign = -1
        else:
            # Handle 'b' refund mode.
            if total_amount < 0:
                default_move_type = 'out_refund' if default_move_type == 'out_invoice' else 'in_refund'
            refund_sign = -1 if 'refund' in default_move_type else 1

        # Write the type as the journal entry is already created.
        invoice.move_type = default_move_type

        # self could be a single record (editing) or be empty (new).
        with Form(invoice.with_context(default_move_type=default_move_type)) as invoice_form:
            partner_type = invoice_form.journal_id.type == 'purchase' and 'SellerTradeParty' or 'BuyerTradeParty'
            invoice_form.partner_id = self._retrieve_partner(
                name=_find_value(f"//ram:{partner_type}/ram:Name"),
                mail=_find_value(f"//ram:{partner_type}//ram:URIID[@schemeID='SMTP']"),
                vat=_find_value(f"//ram:{partner_type}/ram:SpecifiedTaxRegistration/ram:ID"),
            )

            # Reference.
            elements = tree.xpath('//rsm:ExchangedDocument/ram:ID', namespaces=tree.nsmap)
            if elements:
                invoice_form.ref = elements[0].text

            # Name.
            elements = tree.xpath('//ram:BuyerOrderReferencedDocument/ram:IssuerAssignedID', namespaces=tree.nsmap)
            if elements:
                invoice_form.payment_reference = elements[0].text

            # Comment.
            elements = tree.xpath('//ram:IncludedNote/ram:Content', namespaces=tree.nsmap)
            if elements:
                invoice_form.narration = elements[0].text

            # Total amount.
            elements = tree.xpath('//ram:GrandTotalAmount', namespaces=tree.nsmap)
            if elements:

                # Currency.
                currency_str = elements[0].attrib.get('currencyID', None)
                if currency_str:
                    invoice_form.currency_id = self._retrieve_currency(currency_str)

                    # Store xml total amount.
                    amount_total_import = total_amount * refund_sign

            # Date.
            elements = tree.xpath('//rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString', namespaces=tree.nsmap)
            if elements:
                date_str = elements[0].text
                date_obj = datetime.strptime(date_str, DEFAULT_FACTURX_DATE_FORMAT)
                invoice_form.invoice_date = date_obj.strftime(DEFAULT_SERVER_DATE_FORMAT)

            # Due date.
            elements = tree.xpath('//ram:SpecifiedTradePaymentTerms/ram:DueDateDateTime/udt:DateTimeString', namespaces=tree.nsmap)
            if elements:
                date_str = elements[0].text
                date_obj = datetime.strptime(date_str, DEFAULT_FACTURX_DATE_FORMAT)
                invoice_form.invoice_date_due = date_obj.strftime(DEFAULT_SERVER_DATE_FORMAT)

            # Invoice lines.
            elements = tree.xpath('//ram:IncludedSupplyChainTradeLineItem', namespaces=tree.nsmap)
            if elements:
                for element in elements:
                    with invoice_form.invoice_line_ids.new() as invoice_line_form:

                        # Sequence.
                        line_elements = element.xpath('.//ram:AssociatedDocumentLineDocument/ram:LineID', namespaces=tree.nsmap)
                        if line_elements:
                            invoice_line_form.sequence = int(line_elements[0].text)

                        # Product.
                        name = _find_value('.//ram:SpecifiedTradeProduct/ram:Name', element)
                        if name:
                            invoice_line_form.name = name
                        invoice_line_form.product_id = self._retrieve_product(
                            default_code=_find_value('.//ram:SpecifiedTradeProduct/ram:SellerAssignedID', element),
                            name=_find_value('.//ram:SpecifiedTradeProduct/ram:Name', element),
                            barcode=_find_value('.//ram:SpecifiedTradeProduct/ram:GlobalID', element)
                        )

                        # Quantity.
                        line_elements = element.xpath('.//ram:SpecifiedLineTradeDelivery/ram:BilledQuantity', namespaces=tree.nsmap)
                        if line_elements:
                            invoice_line_form.quantity = float(line_elements[0].text)

                        # Price Unit.
                        line_elements = element.xpath('.//ram:GrossPriceProductTradePrice/ram:ChargeAmount', namespaces=tree.nsmap)
                        if line_elements:
                            quantity_elements = element.xpath('.//ram:GrossPriceProductTradePrice/ram:BasisQuantity', namespaces=tree.nsmap)
                            if quantity_elements:
                                invoice_line_form.price_unit = float(line_elements[0].text) / float(quantity_elements[0].text)
                            else:
                                invoice_line_form.price_unit = float(line_elements[0].text)
                        else:
                            line_elements = element.xpath('.//ram:NetPriceProductTradePrice/ram:ChargeAmount', namespaces=tree.nsmap)
                            if line_elements:
                                quantity_elements = element.xpath('.//ram:NetPriceProductTradePrice/ram:BasisQuantity', namespaces=tree.nsmap)
                                if quantity_elements:
                                    invoice_line_form.price_unit = float(line_elements[0].text) / float(quantity_elements[0].text)
                                else:
                                    invoice_line_form.price_unit = float(line_elements[0].text)
                        # Discount.
                        line_elements = element.xpath('.//ram:AppliedTradeAllowanceCharge/ram:CalculationPercent', namespaces=tree.nsmap)
                        if line_elements:
                            invoice_line_form.discount = float(line_elements[0].text)

                        # Taxes
                        tax_element = element.xpath('.//ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:RateApplicablePercent', namespaces=tree.nsmap)
                        invoice_line_form.tax_ids.clear()
                        for eline in tax_element:
                            tax = self._retrieve_tax(
                                amount=eline.text,
                                type_tax_use=invoice_form.journal_id.type
                            )
                            if tax:
                                invoice_line_form.tax_ids.add(tax)

            elif amount_total_import:
                # No lines in BASICWL.
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    invoice_line_form.name = invoice_form.comment or '/'
                    invoice_line_form.quantity = 1
                    invoice_line_form.price_unit = amount_total_import

        return invoice_form.save()
