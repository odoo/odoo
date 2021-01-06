# -*- coding: utf-8 -*-

from odoo import api, models, fields, tools, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_repr
from odoo.tests.common import Form
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype

from datetime import datetime
from lxml import etree
from PyPDF2 import PdfFileReader
from collections import namedtuple

import io
import base64

import logging
_logger = logging.getLogger(__name__)


DEFAULT_FACTURX_DATE_FORMAT = '%Y%m%d'

# Series of helper to handle both attachment as namedtuples or records
def _get_attachment_filename(attachment):
    return hasattr(attachment, 'fname') and getattr(attachment, 'fname') or attachment.name


def _get_attachment_content(attachment):
    return hasattr(attachment, 'content') and getattr(attachment, 'content') or base64.b64decode(attachment.datas)


def _get_attachment_mimetype(attachment):
    if hasattr(attachment, 'mimetype'):
        mimetype = attachment.mimetype
    else:
        try:
            mimetype = guess_mimetype(_get_attachment_content(attachment), default='application/octet-stream')
        except Exception:  # we could refine on base64.binascii.Error and such, but we want to be very lax
            mimetype = 'application/octet-stream'
    return mimetype


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

    @api.multi
    def _export_as_facturx_xml(self):
        ''' Create the Factur-x xml file content.
        :return: The XML content as str.
        '''
        self.ensure_one()

        def format_date(dt):
            # Format the date in the Factur-x standard.
            dt = dt or datetime.now()
            return dt.strftime(DEFAULT_FACTURX_DATE_FORMAT)

        def format_monetary(number, currency):
            # Format the monetary values to avoid trailing decimals (e.g. 90.85000000000001).
            return float_repr(number, currency.decimal_places)

        # Create file content.
        template_values = {
            'record': self,
            'format_date': format_date,
            'format_monetary': format_monetary,
            'invoice_line_values': [],
        }

        # Tax lines.
        aggregated_taxes_details = {line.tax_id.id: {
            'line': line,
            'tax_amount': line.amount,
            'tax_base_amount': 0.0,
        } for line in self.tax_line_ids}

        # Invoice lines.
        for i, line in enumerate(self.invoice_line_ids.filtered(lambda l: not l.display_type)):
            price_unit_with_discount = line.price_unit * (1 - (line.discount / 100.0))
            taxes_res = line.invoice_line_tax_ids.compute_all(
                price_unit_with_discount,
                currency=line.currency_id,
                quantity=line.quantity,
                product=line.product_id,
                partner=self.partner_id,
                is_refund=self.type in ('out_refund', 'in_refund'),
            )

            line_template_values = {
                'line': line,
                'index': i + 1,
                'tax_details': [],
                'net_price_subtotal': taxes_res['total_excluded'],
            }

            for tax_res in taxes_res['taxes']:
                tax = self.env['account.tax'].browse(tax_res['id'])
                line_template_values['tax_details'].append({
                    'tax': tax,
                    'tax_amount': tax_res['amount'],
                    'tax_base_amount': tax_res['base'],
                })

                if tax.id in aggregated_taxes_details:
                    aggregated_taxes_details[tax.id]['tax_base_amount'] += tax_res['base']

            template_values['invoice_line_values'].append(line_template_values)

        template_values['tax_details'] = list(aggregated_taxes_details.values())

        content = self.env.ref('account_facturx.account_invoice_facturx_export').render(template_values)
        return b"<?xml version='1.0' encoding='UTF-8'?>" + content

    @api.multi
    def _import_facturx_invoice(self, tree):
        ''' Extract invoice values from the Factur-x xml tree passed as parameter.

        :param tree: The tree of the Factur-x xml file.
        :return: A dictionary containing account.invoice values to create/update it.
        '''
        amount_total_import = None

        # type must be present in the context to get the right behavior of the _default_journal method (account.invoice).
        # journal_id must be present in the context to get the right behavior of the _default_account method (account.invoice.line).
        journal_id = self._default_journal()
        self_ctx = self.with_context(journal_id=journal_id.id)

        # self could be a single record (editing) or be empty (new).
        view = journal_id.type == 'purchase' and 'account.invoice_supplier_form' or 'account.invoice_form'
        with Form(self_ctx, view=view) as invoice_form:

            # Partner (first step to avoid warning 'Warning! You must first select a partner.').
            partner_type = journal_id.type == 'purchase' and 'SellerTradeParty' or 'BuyerTradeParty'
            elements = tree.xpath('//ram:'+partner_type+'/ram:SpecifiedTaxRegistration/ram:ID', namespaces=tree.nsmap)
            partner = elements and self.env['res.partner'].search([('vat', '=', elements[0].text)], limit=1)
            if not partner:
                elements = tree.xpath('//ram:'+partner_type+'/ram:Name', namespaces=tree.nsmap)
                partner_name = elements and elements[0].text
                partner = elements and self.env['res.partner'].search([('name', 'ilike', partner_name)], limit=1)
            if not partner:
                elements = tree.xpath('//ram:'+partner_type+'//ram:URIID[@schemeID=\'SMTP\']', namespaces=tree.nsmap)
                partner = elements and self.env['res.partner'].search([('email', '=', elements[0].text)], limit=1)
            if partner:
                invoice_form.partner_id = partner

            # Reference.
            elements = tree.xpath('//rsm:ExchangedDocument/ram:ID', namespaces=tree.nsmap)
            if elements:
                invoice_form.reference = elements[0].text

            # Name.
            elements = tree.xpath('//ram:BuyerOrderReferencedDocument/ram:IssuerAssignedID', namespaces=tree.nsmap)
            if elements:
                invoice_form.name = elements[0].text

            # Comment.
            elements = tree.xpath('//ram:IncludedNote/ram:Content', namespaces=tree.nsmap)
            if elements:
                invoice_form.comment = elements[0].text

            # Refund type.
            # There is two modes to handle refund in Factur-X:
            # a) type_code == 380 for invoice, type_code == 381 for refund, all positive amounts.
            # b) type_code == 380, negative amounts in case of refund.
            # To handle both, we consider the 'a' mode and switch to 'b' if a negative amount is encountered.
            elements = tree.xpath('//rsm:ExchangedDocument/ram:TypeCode', namespaces=tree.nsmap)
            type_code = elements[0].text
            refund_sign = type_code == '380' and 1 or -1

            # Total amount.
            elements = tree.xpath('//ram:GrandTotalAmount', namespaces=tree.nsmap)
            if elements:
                total_amount = float(elements[0].text)

                # Handle 'a & b' refund mode.
                if (total_amount < 0 and type_code == '380') or type_code == '381':
                    refund_sign = -1

                # Currency.
                if elements[0].attrib.get('currencyID'):
                    currency_str = elements[0].attrib['currencyID']
                    currency = self.env.ref('base.%s' % currency_str.upper(), raise_if_not_found=False)
                    if currency != self.env.user.company_id.currency_id and currency.active:
                        invoice_form.currency_id = currency

                    # Store xml total amount.
                    amount_total_import = total_amount * refund_sign

            # Date.
            elements = tree.xpath('//rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString', namespaces=tree.nsmap)
            if elements:
                date_str = elements[0].text
                date_obj = datetime.strptime(date_str, DEFAULT_FACTURX_DATE_FORMAT)
                invoice_form.date_invoice = date_obj.strftime(DEFAULT_SERVER_DATE_FORMAT)

            # Due date.
            elements = tree.xpath('//ram:SpecifiedTradePaymentTerms/ram:DueDateDateTime/udt:DateTimeString', namespaces=tree.nsmap)
            if elements:
                date_str = elements[0].text
                date_obj = datetime.strptime(date_str, DEFAULT_FACTURX_DATE_FORMAT)
                # Set to empty record set to avoid readonly on date_due, can not set to False or None in a Form
                invoice_form.payment_term_id = self.env['account.payment.term']
                invoice_form.date_due = date_obj.strftime(DEFAULT_SERVER_DATE_FORMAT)

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
                        line_elements = element.xpath('.//ram:SpecifiedTradeProduct/ram:Name', namespaces=tree.nsmap)
                        if line_elements:
                            invoice_line_form.name = line_elements[0].text
                        line_elements = element.xpath('.//ram:SpecifiedTradeProduct/ram:SellerAssignedID', namespaces=tree.nsmap)
                        if line_elements and line_elements[0].text:
                            product = self.env['product.product'].search([('default_code', '=', line_elements[0].text)])
                            if product:
                                invoice_line_form.product_id = product
                        if not invoice_line_form.product_id:
                            line_elements = element.xpath('.//ram:SpecifiedTradeProduct/ram:GlobalID', namespaces=tree.nsmap)
                            if line_elements and line_elements[0].text:
                                product = self.env['product.product'].search([('barcode', '=', line_elements[0].text)])
                                if product:
                                    invoice_line_form.product_id = product

                        # Quantity.
                        line_elements = element.xpath('.//ram:SpecifiedLineTradeDelivery/ram:BilledQuantity', namespaces=tree.nsmap)
                        if line_elements:
                            invoice_line_form.quantity = float(line_elements[0].text)

                        # Price Unit.
                        line_elements = element.xpath('.//ram:GrossPriceProductTradePrice/ram:ChargeAmount', namespaces=tree.nsmap)
                        if line_elements:
                            invoice_line_form.price_unit = float(line_elements[0].text) / invoice_line_form.quantity
                        else:
                            line_elements = element.xpath('.//ram:NetPriceProductTradePrice/ram:ChargeAmount', namespaces=tree.nsmap)
                            if line_elements:
                                invoice_line_form.price_unit = float(line_elements[0].text) / invoice_line_form.quantity

                        # Discount.
                        line_elements = element.xpath('.//ram:AppliedTradeAllowanceCharge/ram:CalculationPercent', namespaces=tree.nsmap)
                        if line_elements:
                            invoice_line_form.discount = float(line_elements[0].text)

                        # Taxes
                        line_elements = element.xpath('.//ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:RateApplicablePercent', namespaces=tree.nsmap)
                        invoice_line_form.invoice_line_tax_ids.clear()
                        for tax_element in line_elements:
                            percentage = float(tax_element.text)

                            tax = self.env['account.tax'].search([
                                ('company_id', '=', invoice_form.company_id.id),
                                ('amount_type', '=', 'percent'),
                                ('type_tax_use', '=', journal_id.type),
                                ('amount', '=', percentage),
                            ], limit=1)

                            if tax:
                                invoice_line_form.invoice_line_tax_ids.add(tax)
            elif amount_total_import:
                # No lines in BASICWL.
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    invoice_line_form.name = invoice_form.comment or '/'
                    invoice_line_form.quantity = 1
                    invoice_line_form.price_unit = amount_total_import

            # Refund.
            if self_ctx.env.context['journal_type'] == 'purchase':
                invoice_form.type = 'in_refund' if refund_sign == -1 else 'in_invoice'
            else:
                invoice_form.type = 'out_refund' if refund_sign == -1 else 'out_invoice'

        return invoice_form.save()

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        # OVERRIDE
        # /!\ 'default_res_id' in self._context is used to don't process attachment when using a form view.
        res = super(AccountInvoice, self).message_post(**kwargs)

        if 'no_new_invoice' not in self.env.context and len(self) == 1 and self.state == 'draft':
            # Get attachments.
            # - 'attachments' is a namedtuple defined in mail.thread looking like:
            # _Attachment = namedtuple('Attachment', ('fname', 'content', 'info'))
            # - 'attachment_ids' is a list of ir.attachment records ids.
            attachments = kwargs.get('attachments', [])
            if kwargs.get('attachment_ids'):
                attachments += self.env['ir.attachment'].browse(kwargs['attachment_ids'])

            for attachment in attachments:
                self._create_invoice_from_attachment(attachment)
        return res

    @api.one
    def _create_invoice_from_attachment(self, attachment):
        mimetype = _get_attachment_mimetype(attachment)
        if 'pdf' in mimetype:
            self._create_invoice_from_pdf(attachment)
        if 'xml' in mimetype:
            self._create_invoice_from_xml(attachment)

    def _create_invoice_from_pdf(self, attachment):
        filename = _get_attachment_filename(attachment)
        content = _get_attachment_content(attachment)

        with io.BytesIO(content) as buffer:
            try:
                reader = PdfFileReader(buffer)

                # Search for Factur-x embedded file.
                if reader.trailer['/Root'].get('/Names') and reader.trailer['/Root']['/Names'].get('/EmbeddedFiles'):
                    # N.B: embedded_files looks like:
                    # ['file.xml', {'/Type': '/Filespec', '/F': 'file.xml', '/EF': {'/F': IndirectObject(22, 0)}}]
                    embedded_files = reader.trailer['/Root']['/Names']['/EmbeddedFiles']['/Names']
                    # '[::2]' because it's a list [fn_1, content_1, fn_2, content_2, ..., fn_n, content_2]
                    for filename_obj, content_obj in list(zip(embedded_files, embedded_files[1:]))[::2]:
                        content = content_obj.getObject()['/EF']['/F'].getData()
                        try:
                            tree = etree.fromstring(content)
                        except Exception:
                            continue
                        if tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice':
                            self._import_facturx_invoice(tree)
                            buffer.close()

            except Exception as e:
                # Malformed pdf
                _logger.exception(e)

    @api.model
    def _get_xml_decoders(self):
        ''' List of usable decoders to extract invoice from attachments.

        :return: a list of triplet (xml_type, check_func, decode_func)
            * xml_type: The format name, e.g 'UBL 2.1'
            * check_func: A function taking an etree as parameter and returning a dict:
                * flag: The etree is part of this format.
                * error: Error message.
            * decode_func: A function taking an etree as parameter and returning an invoice record.
        '''
        # TO BE OVERWRITTEN
        return []

    @api.multi
    def _create_invoice_from_xml(self, attachment):
        decoders = self._get_xml_decoders()

        # Convert attachment -> etree
        content = _get_attachment_content(attachment)
        try:
            tree = etree.fromstring(content)
        except Exception:
            raise UserError(_('The xml file is badly formatted : {}').format(_get_attachment_filename(attachment)))

        for xml_type, check_func, decode_func in decoders:
            check_res = check_func(tree)

            if check_res.get('flag') and not check_res.get('error'):
                invoice = decode_func(tree)
                if invoice:
                    try:
                        # don't propose to send to ocr
                        invoice.extract_state = 'done'
                    except AttributeError:
                        # account_invoice_exctract not installed
                        pass
                    break

        try:
            return invoice
        except UnboundLocalError:
            raise UserError(_('No decoder was found for the xml file: {}. The file is badly formatted, not supported or the decoder is not installed').format(_get_attachment_filename(attachment)))
