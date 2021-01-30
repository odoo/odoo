# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter
from odoo.osv import expression

from lxml import etree
import base64
import io
import logging

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _name = 'account.edi.format'
    _description = 'EDI format'

    name = fields.Char()
    code = fields.Char(required=True)

    _sql_constraints = [
        ('unique_code', 'unique (code)', 'This code already exists')
    ]


    ####################################################
    # Low-level methods
    ####################################################

    @api.model_create_multi
    def create(self, vals_list):
        edi_formats = super().create(vals_list)

        # activate by default on journal
        journals = self.env['account.journal'].search([])
        for journal in journals:
            for edi_format in edi_formats:
                if edi_format._is_compatible_with_journal(journal):
                    journal.edi_format_ids += edi_format

        # activate cron
        if any(edi_format._needs_web_services() for edi_format in edi_formats):
            self.env.ref('account_edi.ir_cron_edi_network').active = True

        return edi_formats

    ####################################################
    # Export method to override based on EDI Format
    ####################################################

    def _is_required_for_invoice(self, invoice):
        """ Indicate if this EDI must be generated for the invoice passed as parameter.

        :param invoice: An account.move having the invoice type.
        :returns:       True if the EDI must be generated, False otherwise.
        """
        # TO OVERRIDE
        self.ensure_one()
        return True

    def _is_required_for_payment(self, payment):
        """ Indicate if this EDI must be generated for the payment passed as parameter.

        :param payment: An account.move linked to either an account.payment, either an account.bank.statement.line.
        :returns:       True if the EDI must be generated, False otherwise.
        """
        # TO OVERRIDE
        self.ensure_one()
        return False

    def _needs_web_services(self):
        """ Indicate if the EDI must be generated asynchronously through to some web services.

        :return: True if such a web service is available, False otherwise.
        """
        self.ensure_one()
        return False

    def _is_compatible_with_journal(self, journal):
        """ Indicate if the EDI format should appear on the journal passed as parameter to be selected by the user.
        If True, this EDI format will be selected by default on the journal.

        :param journal: The journal.
        :returns:       True if this format can be enabled by default on the journal, False otherwise.
        """
        # TO OVERRIDE
        self.ensure_one()
        return journal.type == 'sale'

    def _is_embedding_to_invoice_pdf_needed(self):
        """ Indicate if the EDI must be embedded inside the PDF report.

        :returns: True if the documents need to be embedded, False otherwise.
        """
        # TO OVERRIDE
        return False

    def _support_batching(self, move=None, state=None, company=None):
        """ Indicate if we can send multiple documents in the same time to the web services.
        If True, the _post_%s_edi methods will get multiple documents in the same time.
        Otherwise, these methods will be called with only one record at a time.

        :returns: True if batching is supported, False otherwise.
        """
        # TO OVERRIDE
        return False

    def _get_batch_key(self, move, state):
        """ Returns a tuple that will be used as key to partitionnate the invoices/payments when creating batches
        with multiple invoices/payments.
        The type of move (invoice or payment), its company_id, its edi state and the edi_format are used by default, if
        no further partition is needed for this format, this method should return ().

        :returns: The key to be used when partitionning the batches.
        """
        move.ensure_one()
        return ()

    def _check_move_configuration(self, move):
        """ Checks the move and relevant records for potential error (missing data, etc).

        :param invoice: The move to check.
        :returns:       A list of error messages.
        """
        # TO OVERRIDE
        return []

    def _post_invoice_edi(self, invoices, test_mode=False):
        """ Create the file content representing the invoice (and calls web services if necessary).

        :param invoices:    A list of invoices to post.
        :param test_mode:   A flag indicating the EDI should only simulate the EDI without sending data.
        :returns:           A dictionary with the invoice as key and as value, another dictionary:
        * attachment:       The attachment representing the invoice in this edi_format if the edi was successfully posted.
        * error:            An error if the edi was not successfully posted.
        * blocking_level:    (optional, requires account_edi_extended) How bad is the error (how should the edi flow be blocked ?)
        """
        # TO OVERRIDE
        self.ensure_one()
        return {}

    def _cancel_invoice_edi(self, invoices, test_mode=False):
        """Calls the web services to cancel the invoice of this document.

        :param invoices:    A list of invoices to cancel.
        :param test_mode:   A flag indicating the EDI should only simulate the EDI without sending data.
        :returns:           A dictionary with the invoice as key and as value, another dictionary:
        * success:          True if the invoice was successfully cancelled.
        * error:            An error if the edi was not successfully cancelled.
        * blocking_level:    (optional, requires account_edi_extended) How bad is the error (how should the edi flow be blocked ?)
        """
        # TO OVERRIDE
        self.ensure_one()
        return {invoice: {'success': True} for invoice in invoices}  # By default, cancel succeeds doing nothing.

    def _post_payment_edi(self, payments, test_mode=False):
        """ Create the file content representing the payment (and calls web services if necessary).

        :param payments:   The payments to post.
        :param test_mode:   A flag indicating the EDI should only simulate the EDI without sending data.
        :returns:           A dictionary with the payment as key and as value, another dictionary:
        * attachment:       The attachment representing the payment in this edi_format if the edi was successfully posted.
        * error:            An error if the edi was not successfully posted.
        * blocking_level:    (optional, requires account_edi_extended) How bad is the error (how should the edi flow be blocked ?)
        """
        # TO OVERRIDE
        self.ensure_one()
        return {}

    def _cancel_payment_edi(self, payments, test_mode=False):
        """Calls the web services to cancel the payment of this document.

        :param payments:  A list of payments to cancel.
        :param test_mode: A flag indicating the EDI should only simulate the EDI without sending data.
        :returns:         A dictionary with the payment as key and as value, another dictionary:
        * success:        True if the payment was successfully cancelled.
        * error:          An error if the edi was not successfully cancelled.
        * blocking_level:  (optional, requires account_edi_extended) How bad is the error (how should the edi flow be blocked ?)
        """
        # TO OVERRIDE
        self.ensure_one()
        return {payment: {'success': True} for payment in payments}  # By default, cancel succeeds doing nothing.

    ####################################################
    # Import methods to override based on EDI Format
    ####################################################

    def _create_invoice_from_xml_tree(self, filename, tree):
        """ Create a new invoice with the data inside the xml.

        :param filename: The name of the xml.
        :param tree:     The tree of the xml to import.
        :returns:        The created invoice.
        """
        # TO OVERRIDE
        self.ensure_one()
        return self.env['account.move']

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        """ Update an existing invoice with the data inside the xml.

        :param filename: The name of the xml.
        :param tree:     The tree of the xml to import.
        :param invoice:  The invoice to update.
        :returns:        The updated invoice.
        """
        # TO OVERRIDE
        self.ensure_one()
        return self.env['account.move']

    def _create_invoice_from_pdf_reader(self, filename, reader):
        """ Create a new invoice with the data inside a pdf.

        :param filename: The name of the pdf.
        :param reader:   The OdooPdfFileReader of the pdf to import.
        :returns:        The created invoice.
        """
        # TO OVERRIDE
        self.ensure_one()

        return self.env['account.move']

    def _update_invoice_from_pdf_reader(self, filename, reader, invoice):
        """ Update an existing invoice with the data inside the pdf.

        :param filename: The name of the pdf.
        :param reader:   The OdooPdfFileReader of the pdf to import.
        :param invoice:  The invoice to update.
        :returns:        The updated invoice.
        """
        # TO OVERRIDE
        self.ensure_one()
        return self.env['account.move']

    ####################################################
    # Export Internal methods (not meant to be overridden)
    ####################################################

    def _embed_edis_to_pdf(self, pdf_content, invoice):
        """ Create the EDI document of the invoice and embed it in the pdf_content.

        :param pdf_content: the bytes representing the pdf to add the EDIs to.
        :param invoice: the invoice to generate the EDI from.
        :returns: the same pdf_content with the EDI of the invoice embed in it.
        """
        attachments = []
        for edi_format in self:
            attachment = invoice._get_edi_attachment(edi_format)
            if attachment and edi_format._is_embedding_to_invoice_pdf_needed():
                datas = base64.b64decode(attachment.with_context(bin_size=False).datas)
                attachments.append({'name': attachment.name, 'datas': datas})

        if attachments:
            # Add the attachments to the pdf file
            reader_buffer = io.BytesIO(pdf_content)
            reader = OdooPdfFileReader(reader_buffer, strict=False)
            writer = OdooPdfFileWriter()
            writer.cloneReaderDocumentRoot(reader)
            for vals in attachments:
                writer.addAttachment(vals['name'], vals['datas'])
            buffer = io.BytesIO()
            writer.write(buffer)
            pdf_content = buffer.getvalue()
            reader_buffer.close()
            buffer.close()
        return pdf_content

    ####################################################
    # Import Internal methods (not meant to be overridden)
    ####################################################

    def _decode_xml(self, filename, content):
        """Decodes an xml into a list of one dictionary representing an attachment.

        :param filename:    The name of the xml.
        :param attachment:  The xml as a string.
        :returns:           A list with a dictionary.
        * filename:         The name of the attachment.
        * content:          The content of the attachment.
        * type:             The type of the attachment.
        * xml_tree:         The tree of the xml if type is xml.
        * pdf_reader:       The pdf_reader if type is pdf.
        """
        to_process = []
        try:
            xml_tree = etree.fromstring(content)
        except Exception as e:
            _logger.exception("Error when converting the xml content to etree: %s" % e)
            return to_process
        if len(xml_tree):
            to_process.append({
                'filename': filename,
                'content': content,
                'type': 'xml',
                'xml_tree': xml_tree,
            })
        return to_process

    def _decode_pdf(self, filename, content):
        """Decodes a pdf and unwrap sub-attachment into a list of dictionary each representing an attachment.

        :param filename:    The name of the pdf.
        :param content:     The bytes representing the pdf.
        :returns:           A list of dictionary for each attachment.
        * filename:         The name of the attachment.
        * content:          The content of the attachment.
        * type:             The type of the attachment.
        * xml_tree:         The tree of the xml if type is xml.
        * pdf_reader:       The pdf_reader if type is pdf.
        """
        to_process = []
        try:
            buffer = io.BytesIO(content)
            pdf_reader = OdooPdfFileReader(buffer, strict=False)
        except Exception as e:
            # Malformed pdf
            _logger.exception("Error when reading the pdf: %s" % e)
            return to_process

        # Process embedded files.
        try:
            for xml_name, content in pdf_reader.getAttachments():
                to_process.extend(self._decode_xml(xml_name, content))
        except NotImplementedError as e:
            _logger.warning("Unable to access the attachments of %s. Tried to decrypt it, but %s." % (filename, e))

        # Process the pdf itself.
        to_process.append({
            'filename': filename,
            'content': content,
            'type': 'pdf',
            'pdf_reader': pdf_reader,
        })

        return to_process

    def _decode_attachment(self, attachment):
        """Decodes an ir.attachment and unwrap sub-attachment into a list of dictionary each representing an attachment.

        :param attachment:  An ir.attachment record.
        :returns:           A list of dictionary for each attachment.
        * filename:         The name of the attachment.
        * content:          The content of the attachment.
        * type:             The type of the attachment.
        * xml_tree:         The tree of the xml if type is xml.
        * pdf_reader:       The pdf_reader if type is pdf.
        """
        content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        to_process = []

        if 'pdf' in attachment.mimetype:
            to_process.extend(self._decode_pdf(attachment.name, content))
        elif 'xml' in attachment.mimetype:
            to_process.extend(self._decode_xml(attachment.name, content))

        return to_process

    def _create_invoice_from_attachment(self, attachment):
        """Decodes an ir.attachment to create an invoice.

        :param attachment:  An ir.attachment record.
        :returns:           The invoice where to import data.
        """
        for file_data in self._decode_attachment(attachment):
            for edi_format in self:
                res = False
                try:
                    if file_data['type'] == 'xml':
                        res = edi_format._create_invoice_from_xml_tree(file_data['filename'], file_data['xml_tree'])
                    elif file_data['type'] == 'pdf':
                        res = edi_format._create_invoice_from_pdf_reader(file_data['filename'], file_data['pdf_reader'])
                        file_data['pdf_reader'].stream.close()
                except Exception as e:
                    _logger.exception("Error importing attachment \"%s\" as invoice with format \"%s\"", file_data['filename'], edi_format.name, str(e))
                if res:
                    if 'extract_state' in res:
                        # Bypass the OCR to prevent overwriting data when an EDI was succesfully imported.
                        # TODO : remove when we integrate the OCR to the EDI flow.
                        res.write({'extract_state': 'done'})
                    return res
        return self.env['account.move']

    def _update_invoice_from_attachment(self, attachment, invoice):
        """Decodes an ir.attachment to update an invoice.

        :param attachment:  An ir.attachment record.
        :returns:           The invoice where to import data.
        """
        for file_data in self._decode_attachment(attachment):
            for edi_format in self:
                res = False
                try:
                    if file_data['type'] == 'xml':
                        res = edi_format._update_invoice_from_xml_tree(file_data['filename'], file_data['xml_tree'], invoice)
                    elif file_data['type'] == 'pdf':
                        res = edi_format._update_invoice_from_pdf_reader(file_data['filename'], file_data['pdf_reader'], invoice)
                        file_data['pdf_reader'].stream.close()
                except Exception as e:
                    _logger.exception("Error importing attachment \"%s\" as invoice with format \"%s\"", file_data['filename'], edi_format.name, str(e))
                if res:
                    if 'extract_state' in res:
                        # Bypass the OCR to prevent overwriting data when an EDI was succesfully imported.
                        # TODO : remove when we integrate the OCR to the EDI flow.
                        res.write({'extract_state': 'done'})
                    return res
        return self.env['account.move']

    ####################################################
    # Import helpers
    ####################################################

    def _find_value(self, xpath, xml_element, namespaces=None):
        element = xml_element.xpath(xpath, namespaces=namespaces)
        return element[0].text if element else None

    def _retrieve_partner(self, name=None, phone=None, mail=None, vat=None):
        '''Search all partners and find one that matches one of the parameters.

        :param name:    The name of the partner.
        :param phone:   The phone or mobile of the partner.
        :param mail:    The mail of the partner.
        :param vat:     The vat number of the partner.
        :returns:       A partner or an empty recordset if not found.
        '''
        domains = []
        for value, domain in (
            (name, [('name', 'ilike', name)]),
            (phone, expression.OR([[('phone', '=', phone)], [('mobile', '=', phone)]])),
            (mail, [('email', '=', mail)]),
            (vat, [('vat', 'like', vat)]),
        ):
            if value is not None:
                domains.append(domain)

        domain = expression.OR(domains)
        return self.env['res.partner'].search(domain, limit=1)

    def _retrieve_product(self, name=None, default_code=None, barcode=None):
        '''Search all products and find one that matches one of the parameters.

        :param name:            The name of the product.
        :param default_code:    The default_code of the product.
        :param barcode:         The barcode of the product.
        :returns:               A product or an empty recordset if not found.
        '''
        domains = []
        for value, domain in (
            (name, ('name', 'ilike', name)),
            (default_code, ('default_code', '=', default_code)),
            (barcode, ('barcode', '=', barcode)),
        ):
            if value is not None:
                domains.append([domain])

        domain = expression.OR(domains)
        return self.env['product.product'].search(domain, limit=1)

    def _retrieve_tax(self, amount, type_tax_use):
        '''Search all taxes and find one that matches all of the parameters.

        :param amount:          The amount of the tax.
        :param type_tax_use:    The type of the tax.
        :returns:               A tax or an empty recordset if not found.
        '''
        domains = [
            [('amount', '=', float(amount))],
            [('type_tax_use', '=', type_tax_use)]
        ]

        return self.env['account.tax'].search(expression.AND(domains), order='sequence ASC', limit=1)

    def _retrieve_currency(self, code):
        '''Search all currencies and find one that matches the code.

        :param code: The code of the currency.
        :returns:    A currency or an empty recordset if not found.
        '''
        return self.env['res.currency'].search([('name', '=', code.upper())], limit=1)

    ####################################################
    # Other helpers
    ####################################################

    @api.model
    def _format_error_message(self, error_title, errors):
        bullet_list_msg = ''.join('<li>%s</li>' % msg for msg in errors)
        return '%s<ul>%s</ul>' % (error_title, bullet_list_msg)
