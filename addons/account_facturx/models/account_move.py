# -*- coding: utf-8 -*-

from odoo import api, models, fields, tools, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_repr
from odoo.tests.common import Form
from odoo.exceptions import UserError, except_orm

from datetime import datetime
from lxml import etree
from PyPDF2 import PdfFileReader

import io
import base64

import logging
_logger = logging.getLogger(__name__)


DEFAULT_FACTURX_DATE_FORMAT = '%Y%m%d'


class AccountMove(models.Model):
    _inherit = 'account.move'

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
        }
        content = self.env.ref('account_facturx.account_invoice_facturx_export').render(template_values)
        return b"<?xml version='1.0' encoding='UTF-8'?>" + content

    def _import_facturx_invoice(self, tree):
        ''' Extract invoice values from the Factur-x xml tree passed as parameter.

        :param tree: The tree of the Factur-x xml file.
        :return: A dictionary containing account.invoice values to create/update it.
        '''
        amount_total_import = None

        if self._context.get('default_journal_id'):
            journal = self.env['account.journal'].browse(self.env.context['default_journal_id'])
            default_type = 'out_invoice' if journal.type == 'sale' else 'in_invoice'
        elif self._context.get('default_type'):
            default_type = self._context['default_type']
        else:
            raise UserError(_("No information about the journal or the type of invoice is passed"))

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

        if type_code == '381':
            default_type = 'out_refund' if default_type == 'out_invoice' else 'in_refund'
            refund_sign = -1
        else:
            # Handle 'b' refund mode.
            if total_amount < 0:
                default_type = 'out_refund' if default_type == 'out_invoice' else 'in_refund'
            refund_sign = -1 if 'refund' in default_type else 1

        # Write the type as the journal entry is already created.
        self.type = default_type

        # self could be a single record (editing) or be empty (new).
        with Form(self.with_context(default_type=default_type)) as invoice_form:
            # Partner (first step to avoid warning 'Warning! You must first select a partner.').
            partner_type = invoice_form.journal_id.type == 'purchase' and 'SellerTradeParty' or 'BuyerTradeParty'
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
                invoice_form.ref = elements[0].text

            # Name.
            elements = tree.xpath('//ram:BuyerOrderReferencedDocument/ram:IssuerAssignedID', namespaces=tree.nsmap)
            if elements:
                invoice_form.invoice_payment_ref = elements[0].text

            # Comment.
            elements = tree.xpath('//ram:IncludedNote/ram:Content', namespaces=tree.nsmap)
            if elements:
                invoice_form.narration = elements[0].text

            # Total amount.
            elements = tree.xpath('//ram:GrandTotalAmount', namespaces=tree.nsmap)
            if elements:

                # Currency.
                if elements[0].attrib.get('currencyID'):
                    currency_str = elements[0].attrib['currencyID']
                    currency = self.env.ref('base.%s' % currency_str.upper(), raise_if_not_found=False)
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
                        invoice_line_form.tax_ids.clear()
                        for tax_element in line_elements:
                            percentage = float(tax_element.text)

                            tax = self.env['account.tax'].search([
                                ('company_id', '=', invoice_form.company_id.id),
                                ('amount_type', '=', 'percent'),
                                ('type_tax_use', '=', invoice_form.journal_id.type),
                                ('amount', '=', percentage),
                            ], limit=1)

                            if tax:
                                invoice_line_form.tax_ids.add(tax)
            elif amount_total_import:
                # No lines in BASICWL.
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    invoice_line_form.name = invoice_form.comment or '/'
                    invoice_line_form.quantity = 1
                    invoice_line_form.price_unit = amount_total_import

        return invoice_form.save()

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        # OVERRIDE
        # /!\ 'default_res_id' in self._context is used to don't process attachment when using a form view.
        res = super(AccountMove, self).message_post(**kwargs)

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

    def _create_invoice_from_attachment(self, attachment):
        if 'pdf' in attachment.mimetype:
            for move in self:
                move._create_invoice_from_pdf(attachment)
        if 'xml' in attachment.mimetype:
            for move in self:
                move._create_invoice_from_xml(attachment)

    def _create_invoice_from_pdf(self, attachment):
        def _get_attachment_filename(attachment):
            # Handle both _Attachment namedtuple in mail.thread or ir.attachment.
            return hasattr(attachment, 'fname') and getattr(attachment, 'fname') or attachment.name

        def _get_attachment_content(attachment):
            # Handle both _Attachment namedtuple in mail.thread or ir.attachment.
            return hasattr(attachment, 'content') and getattr(attachment, 'content') or base64.b64decode(attachment.datas)
        filename = _get_attachment_filename(attachment)

        # Check if the attachment is a pdf.
        if not filename.endswith('.pdf'):
            return

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

                        if filename_obj == 'factur-x.xml':
                            try:
                                tree = etree.fromstring(content)
                            except Exception:
                                continue

                            self._import_facturx_invoice(tree)
                            buffer.close()
            except except_orm as e:
                raise e
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

    def _create_invoice_from_xml(self, attachment):
        decoders = self._get_xml_decoders()

        # Convert attachment -> etree
        content = base64.b64decode(attachment.datas)
        try:
            tree = etree.fromstring(content)
        except Exception:
            raise UserError(_('The xml file is badly formatted : {}').format(attachment.name))

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
            raise UserError(_('No decoder was found for the xml file: {}. The file is badly formatted, not supported or the decoder is not installed').format(attachment.name))
