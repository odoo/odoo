# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

import base64
import io
import logging

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'


    ####################################################
    # Low-level methods
    ####################################################

    @api.model_create_multi
    def create(self, vals_list):
        edi_formats = super().create(vals_list)

        # activate by default on journal
        journals = self.env['account.journal'].search([])
        journals._compute_edi_format_ids()

        return edi_formats

    ####################################################
    # Export method to override based on EDI Format
    ####################################################

    def _get_edi_priority(self):
        priorities = super()._get_edi_priority()
        priorities.update(
            invoice=0,
            payment=10,
        )
        return priorities

    def _is_compatible_with_journal(self, journal):
        """ Indicate if the EDI format should appear on the journal passed as parameter to be selected by the user.
        If True, this EDI format will appear on the journal.

        :param journal: The journal.
        :returns:       True if this format can appear on the journal, False otherwise.
        """
        # TO OVERRIDE
        self.ensure_one()
        return journal.type == 'sale'

    def _is_enabled_by_default_on_journal(self, journal):
        """ Indicate if the EDI format should be selected by default on the journal passed as parameter.
        If True, this EDI format will be selected by default on the journal.

        :param journal: The journal.
        :returns:       True if this format should be enabled by default on the journal, False otherwise.
        """
        return True

    def _is_required_for_record(self, rec, edi_type):
        if edi_type == 'invoice':
            return self._is_required_for_invoice(rec)
        if edi_type == 'payment':
            return self._is_required_for_payment(rec)

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

    def _is_embedding_to_invoice_pdf_needed(self):
        """ Indicate if the EDI must be embedded inside the PDF report.

        :returns: True if the documents need to be embedded, False otherwise.
        """
        # TO OVERRIDE
        return False

    def _get_embedding_to_invoice_pdf_values(self, invoice):
        """ Get the values to embed to pdf.

        :returns:   A dictionary {'name': name, 'datas': datas} or False if there are no values to embed.
        * name:     The name of the file.
        * datas:    The bytes ot the file.
        """
        self.ensure_one()
        attachment = invoice._get_edi_attachment(self)
        if not attachment or not self._is_embedding_to_invoice_pdf_needed():
            return False
        datas = base64.b64decode(attachment.with_context(bin_size=False).datas)
        return {'name': attachment.name, 'datas': datas}

    def _check_record_configuration(self, rec, edi_type):
        if edi_type in ('invoice', 'payment'):
            return self._check_move_configuration(rec)
        return super()._check_record_configuration(rec, edi_type)

    def _check_move_configuration(self, move):
        # TO OVERRIDE
        return []

    def _post_edi(self, recs, edi_type):
        if edi_type == 'invoice':
            return self._post_invoice_edi(recs)
        if edi_type == 'payment':
            return self._post_payment_edi(recs)
        return super()._post_edi(recs, edi_type)

    def _cancel_edi(self, recs, edi_type):
        if edi_type == 'invoice':
            return self._cancel_invoice_edi(recs)
        if edi_type == 'payment':
            return self._cancel_payment_edi(recs)
        return super()._cancel_edi(recs, edi_type)

    def _post_invoice_edi(self, invoices):
        """ See _post_edi.
        """
        # TO OVERRIDE
        self.ensure_one()
        return {}

    def _cancel_invoice_edi(self, invoices):
        """ See _cancel_edi.
        """
        # TO OVERRIDE
        self.ensure_one()
        return {invoice: {'success': True} for invoice in invoices}  # By default, cancel succeeds doing nothing.

    def _post_payment_edi(self, payments):
        """ See _post_edi.
        """
        # TO OVERRIDE
        self.ensure_one()
        return {}

    def _cancel_payment_edi(self, payments):
        """ See _cancel_edi.
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

    def _create_invoice_from_binary(self, filename, content, extension):
        """ Create a new invoice with the data inside a binary file.

        :param filename:  The name of the file.
        :param content:   The content of the binary file.
        :param extension: The extensions as a string.
        :returns:         The created invoice.
        """
        # TO OVERRIDE
        self.ensure_one()
        return self.env['account.move']

    def _update_invoice_from_binary(self, filename, content, extension, invoice):
        """ Update an existing invoice with the data inside a binary file.

        :param filename: The name of the file.
        :param content:  The content of the binary file.
        :param extension: The extensions as a string.
        :param invoice:  The invoice to update.
        :returns:        The updated invoice.
        """
        # TO OVERRIDE
        self.ensure_one()
        return self.env['account.move']

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
                        res = edi_format.with_company(self.env.company)._create_invoice_from_xml_tree(file_data['filename'], file_data['xml_tree'])
                    elif file_data['type'] == 'pdf':
                        res = edi_format.with_company(self.env.company)._create_invoice_from_pdf_reader(file_data['filename'], file_data['pdf_reader'])
                        file_data['pdf_reader'].stream.close()
                    else:
                        res = edi_format._create_invoice_from_binary(file_data['filename'], file_data['content'], file_data['extension'])
                except Exception as e:
                    _logger.exception("Error importing attachment \"%s\" as invoice with format \"%s\"", file_data['filename'], edi_format.name, str(e))
                if res:
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
                        res = edi_format.with_company(self.env.company)._update_invoice_from_xml_tree(file_data['filename'], file_data['xml_tree'], invoice)
                    elif file_data['type'] == 'pdf':
                        res = edi_format.with_company(self.env.company)._update_invoice_from_pdf_reader(file_data['filename'], file_data['pdf_reader'], invoice)
                        file_data['pdf_reader'].stream.close()
                    else:  # file_data['type'] == 'binary'
                        res = edi_format._update_invoice_from_binary(file_data['filename'], file_data['content'], file_data['extension'], invoice)
                except Exception as e:
                    _logger.exception("Error importing attachment \"%s\" as invoice with format \"%s\"", file_data['filename'], edi_format.name, str(e))
                if res:
                    return res
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
        for edi_format in self.filtered(lambda edi_format: edi_format._is_embedding_to_invoice_pdf_needed()):
            attach = edi_format._get_embedding_to_invoice_pdf_values(invoice)
            if attach:
                attachments.append(attach)

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
