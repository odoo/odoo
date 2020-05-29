# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

from lxml import etree
import base64
import io
import logging

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _name = 'account.edi.format'
    _description = 'EDI format'

    name = fields.Char()
    code = fields.Char()
    hide_on_journal = fields.Selection([('import_export', 'Import/Export'), ('import', 'Import Only')], default='import_export', help='used to hide this EDI format on journals')

    _sql_constraints = [
        ('unique_code', 'unique (code)', 'This code already exists')
    ]

    ####################################################
    # Export method to override based on EDI Format
    ####################################################

    def _export_invoice_to_attachment(self, invoice):
        """ Create the file content representing the invoice.

        :param invoice: the invoice to encode.
        :returns: a dictionary (values are compatible to create an ir.attachment)
        * name : the name of the file
        * datas : the content of the file,
        * res_model : 'account.move',
        * res_id: the id of invoice
        * mimetype : the mimetype of the attachment
        """
        # TO OVERRIDE
        self.ensure_one()
        return False

    def _export_invoice_to_embed_to_pdf(self, pdf_content, invoice):
        """ Create the file content representing the invoice when it's destined
            to be embed into a pdf.
            - default: creates the default EDI document (_export_invoice_to_attachment).
            - Should return False if this EDI format should not be embedded.
            - Should be overriden only if a specific behavior (for example,
            include the pdf content inside the file).

            :param pdf_content: the pdf before any EDI format was added.
            :param invoice: the invoice to add.
            :returns: a dictionary or False if this EDI format must not be embedded to pdf.
            * name : the name of the file
            * datas : the content of the file,
            * res_model : 'account.move',
            * res_id: the id of invoice
            * mimetype : the mimetype of the attachment
        """
        # TO OVERRIDE
        self.ensure_one()
        return self._export_invoice_to_attachment(invoice)

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
            try:
                vals = edi_format._export_invoice_to_embed_to_pdf(pdf_content, invoice)
            except:
                continue
            if vals:
                attachments.append(vals)

        if attachments:
            # Add the attachments to the pdf file
            reader_buffer = io.BytesIO(pdf_content)
            reader = OdooPdfFileReader(reader_buffer)
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

    def _create_ir_attachments(self, invoice):
        """ Create ir.attachment for the EDIs from invoice.

        :param invoice: the invoice to generate the EDI from.
        :returns: the newly created attachments.
        """
        attachment_vals_list = []
        for edi_format in self:
            vals = edi_format._export_invoice_to_attachment(invoice)
            if vals:
                vals['datas'] = base64.encodebytes(vals['datas'])
                vals['edi_format_id'] = edi_format._origin.id
                attachment_vals_list.append(vals)
        res = self.env['ir.attachment'].create(attachment_vals_list)
        invoice.edi_document_ids |= res
        return res

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
            pdf_reader = OdooPdfFileReader(buffer)
        except Exception as e:
            # Malformed pdf
            _logger.exception("Error when reading the pdf: %s" % e)
            return to_process

        # Process embedded files.
        for xml_name, content in pdf_reader.getAttachments():
            to_process.extend(self._decode_xml(xml_name, content))

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
                if file_data['type'] == 'xml':
                    res = edi_format._create_invoice_from_xml_tree(file_data['filename'], file_data['xml_tree'])
                elif file_data['type'] == 'pdf':
                    res = edi_format._create_invoice_from_pdf_reader(file_data['filename'], file_data['pdf_reader'])
                    file_data['pdf_reader'].stream.close()
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
                if file_data['type'] == 'xml':
                    res = edi_format._update_invoice_from_xml_tree(file_data['filename'], file_data['xml_tree'], invoice)
                elif file_data['type'] == 'pdf':
                    res = edi_format._update_invoice_from_pdf_reader(file_data['filename'], file_data['pdf_reader'], invoice)
                    file_data['pdf_reader'].stream.close()
                if res:
                    if 'extract_state' in res:
                        # Bypass the OCR to prevent overwriting data when an EDI was succesfully imported.
                        # TODO : remove when we integrate the OCR to the EDI flow.
                        res.write({'extract_state': 'done'})
                    return res
        return self.env['account.move']
