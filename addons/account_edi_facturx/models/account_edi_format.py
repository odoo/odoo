# -*- coding: utf-8 -*-

from odoo import api, models, fields, tools, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_repr, str2bool
from odoo.tests.common import Form
from odoo.exceptions import RedirectWarning, UserError

from datetime import datetime
from lxml import etree
from PyPDF2 import PdfFileReader
import base64

import io

import logging

_logger = logging.getLogger(__name__)


DEFAULT_FACTURX_DATE_FORMAT = '%Y%m%d'


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        res = super()._is_compatible_with_journal(journal)
        if self.code != 'facturx_1_0_05' or self._is_account_edi_ubl_cii_available():
            return res
        return journal.type == 'sale'

    def _post_invoice_edi(self, invoices, test_mode=False):
        self.ensure_one()
        if self.code != 'facturx_1_0_05' or self._is_account_edi_ubl_cii_available():
            return super()._post_invoice_edi(invoices, test_mode=test_mode)
        res = {}
        for invoice in invoices:
            attachment = self._export_facturx(invoice)
            res[invoice] = {'attachment': attachment}
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
        if self.code != 'facturx_1_0_05' or self._is_account_edi_ubl_cii_available():
            return super()._prepare_invoice_report(pdf_writer, edi_document)
        if not edi_document.attachment_id:
            return

        pdf_writer.embed_odoo_attachment(edi_document.attachment_id, subtype='text/xml')
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
                }))

    def _export_facturx(self, invoice):

        def format_date(dt):
            # Format the date in the Factur-x standard.
            dt = dt or datetime.now()
            return dt.strftime(DEFAULT_FACTURX_DATE_FORMAT)

        def format_monetary(number, currency):
            # Format the monetary values to avoid trailing decimals (e.g. 90.85000000000001).
            if currency.is_zero(number):  # Ensure that we never return -0.0
                number = 0.0
            return float_repr(number, currency.decimal_places)

        self.ensure_one()
        # Create file content.
        seller_siret = 'siret' in invoice.company_id._fields and invoice.company_id.siret or invoice.company_id.company_registry
        buyer_siret = 'siret' in invoice.commercial_partner_id._fields and invoice.commercial_partner_id.siret
        template_values = {
            'record': invoice,
            'format_date': format_date,
            'format_monetary': format_monetary,
            'invoice_line_values': [],
            'seller_specified_legal_organization': seller_siret,
            'buyer_specified_legal_organization': buyer_siret,
            # Chorus PRO fields
            'buyer_reference': 'buyer_reference' in invoice._fields and invoice.buyer_reference or '',
            'contract_reference': 'contract_reference' in invoice._fields and invoice.contract_reference or '',
            'purchase_order_reference': 'purchase_order_reference' in invoice._fields and invoice.purchase_order_reference or '',
        }
        # Tax lines.
        # The old system was making one total "line" per tax in the xml, by using the tax_line_id.
        # The new one is making one total "line" for each tax category and rate group.
        aggregated_taxes_details = invoice._prepare_edi_tax_details(
            grouping_key_generator=lambda tax_values: {
                'unece_tax_category_code': tax_values['tax_id']._get_unece_category_code(invoice.commercial_partner_id, invoice.company_id),
                'amount': tax_values['tax_id'].amount
            }
        )['tax_details']

        balance_multiplicator = -1 if invoice.is_inbound() else 1
        # Map the new keys from the backported _prepare_edi_tax_details into the old ones for compatibility with the old
        # template. Also apply the multiplication here for consistency between the old and new template.
        for tax_detail in aggregated_taxes_details.values():
            tax_detail['tax_base_amount'] = balance_multiplicator * tax_detail['base_amount_currency']
            tax_detail['tax_amount'] = balance_multiplicator * tax_detail['tax_amount_currency']

            # The old template would get the amount from a tax line given to it, while
            # the new one would get the amount from the dictionary returned by _prepare_edi_tax_details directly.
            # As the line was only used to get the tax amount, giving it any line with the same amount will give a correct
            # result even if the tax line doesn't make much sense as this is a total that is not linked to a specific tax.
            # I don't have a solution for 0% taxes, we will give an empty line that will allow to render the xml, but it
            # won't be completely correct. (The RateApplicablePercent will be missing for that line)
            tax_detail['line'] = invoice.line_ids.filtered(lambda l: l.tax_line_id and l.tax_line_id.amount == tax_detail['amount'])[:1]

        # Invoice lines.
        for i, line in enumerate(invoice.invoice_line_ids.filtered(lambda l: not l.display_type)):
            price_unit_with_discount = line.price_unit * (1 - (line.discount / 100.0))
            taxes_res = line.tax_ids.with_context(force_sign=line.move_id._get_tax_force_sign()).compute_all(
                price_unit_with_discount,
                currency=line.currency_id,
                quantity=line.quantity,
                product=line.product_id,
                partner=invoice.partner_id,
                is_refund=line.move_id.move_type in ('in_refund', 'out_refund'),
            )

            if line.discount == 100.0:
                gross_price_subtotal = line.currency_id.round(line.price_unit * line.quantity)
            else:
                gross_price_subtotal = line.currency_id.round(line.price_subtotal / (1 - (line.discount / 100.0)))
            line_template_values = {
                'line': line,
                'index': i + 1,
                'tax_details': [],
                'net_price_subtotal': taxes_res['total_excluded'],
                'price_discount_unit': (gross_price_subtotal - line.price_subtotal) / line.quantity if line.quantity else 0.0,
                'unece_uom_code': line.product_id.product_tmpl_id.uom_id._get_unece_code(),
            }

            for tax_res in taxes_res['taxes']:
                tax = self.env['account.tax'].browse(tax_res['id'])
                tax_category_code = tax._get_unece_category_code(invoice.commercial_partner_id, invoice.company_id)
                line_template_values['tax_details'].append({
                    'tax': tax,
                    'tax_amount': tax_res['amount'],
                    'tax_base_amount': tax_res['base'],
                    'unece_tax_category_code': tax_category_code,
                })

            template_values['invoice_line_values'].append(line_template_values)

        template_values['tax_details'] = list(aggregated_taxes_details.values())

        xml_content = b"<?xml version='1.0' encoding='UTF-8'?>"
        xml_content += self.env.ref('account_edi_facturx.account_invoice_facturx_export')._render(template_values)
        return self.env['ir.attachment'].create({
            'name': 'factur-x.xml',
            'datas': base64.encodebytes(xml_content),
            'mimetype': 'application/xml'
        })

    def _is_facturx(self, filename, tree):
        return self.code == 'facturx_1_0_05' and tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice'

    def _create_invoice_from_xml_tree(self, filename, tree, journal=None):
        self.ensure_one()
        if self._is_facturx(filename, tree) and not self._is_account_edi_ubl_cii_available():
            return self._import_facturx(tree, self.env['account.move'])
        return super()._create_invoice_from_xml_tree(filename, tree, journal=journal)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self._is_facturx(filename, tree) and not self._is_account_edi_ubl_cii_available():
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
            self_ctx = self.with_company(invoice.company_id)

            # Partner (first step to avoid warning 'Warning! You must first select a partner.').
            partner_type = invoice_form.journal_id.type == 'purchase' and 'SellerTradeParty' or 'BuyerTradeParty'
            invoice_form.partner_id = self_ctx._retrieve_partner(
                name=self._find_value('//ram:' + partner_type + '/ram:Name', tree, namespaces=tree.nsmap),
                mail=self._find_value('//ram:' + partner_type + '//ram:URIID[@schemeID=\'SMTP\']', tree, namespaces=tree.nsmap),
                vat=self._find_value('//ram:' + partner_type + '/ram:SpecifiedTaxRegistration/ram:ID', tree, namespaces=tree.nsmap),
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

            # Get currency string for new invoices, or invoices coming from outside
            elements = tree.xpath('//ram:InvoiceCurrencyCode', namespaces=tree.nsmap)
            if elements:
                currency_str = elements[0].text
            # Fallback for old invoices from odoo where the InvoiceCurrencyCode was not present
            else:
                elements = tree.xpath('//ram:TaxTotalAmount', namespaces=tree.nsmap)
                if elements:
                    currency_str = elements[0].attrib['currencyID']

            currency = self.env.ref('base.%s' % currency_str.upper(), raise_if_not_found=False)
            if currency and not currency.active:
                error_msg = _('The currency (%s) of the document you are uploading is not active in this database.\n'
                              'Please activate it before trying again to import.', currency.name)
                error_action = {
                    'view_mode': 'form',
                    'res_model': 'res.currency',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'res_id': currency.id,
                    'views': [[False, 'form']]
                }
                raise RedirectWarning(error_msg, error_action, _('Display the currency'))
            if currency != self.env.company.currency_id and currency.active:
                invoice_form.currency_id = currency

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
                        invoice_line_form.product_id = self_ctx._retrieve_product(
                            default_code=_find_value('.//ram:SpecifiedTradeProduct/ram:SellerAssignedID', element),
                            name=_find_value('.//ram:SpecifiedTradeProduct/ram:Name', element),
                            barcode=_find_value('.//ram:SpecifiedTradeProduct/ram:GlobalID', element)
                        )
                        # force original line description instead of the one copied from product's Sales Description
                        if name:
                            invoice_line_form.name = name

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
                            # For Gross price, we need to check if a discount must be taken into account
                            discount_elements = element.xpath('.//ram:AppliedTradeAllowanceCharge',
                                                          namespaces=tree.nsmap)
                            if discount_elements:
                                discount_percent_elements = element.xpath(
                                    './/ram:AppliedTradeAllowanceCharge/ram:CalculationPercent', namespaces=tree.nsmap)
                                if discount_percent_elements:
                                    invoice_line_form.discount = float(discount_percent_elements[0].text)
                                else:
                                    # if discount not available, it will be computed from the gross and net prices.
                                    net_price_elements = element.xpath('.//ram:NetPriceProductTradePrice/ram:ChargeAmount',
                                                                  namespaces=tree.nsmap)
                                    if net_price_elements:
                                        quantity_elements = element.xpath(
                                            './/ram:NetPriceProductTradePrice/ram:BasisQuantity', namespaces=tree.nsmap)
                                        net_unit_price = float(net_price_elements[0].text) / float(quantity_elements[0].text) \
                                            if quantity_elements else float(net_price_elements[0].text)
                                        invoice_line_form.discount = (invoice_line_form.price_unit - net_unit_price) / invoice_line_form.price_unit * 100.0
                        else:
                            line_elements = element.xpath('.//ram:NetPriceProductTradePrice/ram:ChargeAmount', namespaces=tree.nsmap)
                            if line_elements:
                                quantity_elements = element.xpath('.//ram:NetPriceProductTradePrice/ram:BasisQuantity', namespaces=tree.nsmap)
                                if quantity_elements:
                                    invoice_line_form.price_unit = float(line_elements[0].text) / float(quantity_elements[0].text)
                                else:
                                    invoice_line_form.price_unit = float(line_elements[0].text)

                        # Taxes
                        tax_element = element.xpath('.//ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:RateApplicablePercent', namespaces=tree.nsmap)
                        invoice_line_form.tax_ids.clear()
                        for eline in tax_element:
                            tax = self_ctx._retrieve_tax(
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
