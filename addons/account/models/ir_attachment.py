# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.tools.pdf import OdooPdfFileReader

from lxml import etree
from struct import error as StructError
import io
import logging

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    @api.model
    def _decode_edi_xml(self, filename, content):
        """Decodes an xml into a list of one dictionary representing an attachment.
        :returns:           A list with a dictionary.
        """
        self.ensure_one()
        try:
            xml_tree = etree.fromstring(content)
        except Exception as e:
            _logger.exception("Error when converting the xml content to etree: %s", e)
            return []

        to_process = []
        if xml_tree is not None:
            to_process.append({
                'filename': filename,
                'content': content,
                'xml_tree': xml_tree,
                'sort_weight': 10,
                'type': 'xml',
            })
        return to_process

    def _decode_edi_pdf(self, filename, content):
        """Decodes a pdf and unwrap sub-attachment into a list of dictionary each representing an attachment.
        :returns:           A list of dictionary for each attachment.
        """
        try:
            buffer = io.BytesIO(content)
            pdf_reader = OdooPdfFileReader(buffer, strict=False)
        except Exception as e:
            # Malformed pdf
            _logger.exception("Error when reading the pdf: %s", e)
            return []

        # Process embedded files.
        to_process = []
        try:
            for xml_name, xml_content in pdf_reader.getAttachments():
                to_process.extend(self._decode_edi_xml(xml_name, xml_content))
        except (NotImplementedError, StructError) as e:
            _logger.warning("Unable to access the attachments of %s. Tried to decrypt it, but %s.", filename, e)

        # Process the pdf itself.
        to_process.append({
            'filename': filename,
            'content': content,
            'pdf_reader': pdf_reader,
            'attachment': self,
            'on_close': buffer.close,
            'sort_weight': 20,
            'type': 'pdf',
        })

        return to_process

    def _decode_edi_binary(self, filename, content):
        """Decodes any file into a list of one dictionary representing an attachment.
        This is a fallback for all files that are not decoded by other methods.
        :returns:           A list with a dictionary.
        """
        return [{
            'filename': filename,
            'content': content,
            'attachment': self,
            'sort_weight': 100,
            'type': 'binary',
        }]

    @api.model
    def _get_edi_supported_formats(self):
        """Get the list of supported formats.
        This function is meant to be overriden to add formats.

        :returns:           A list of dictionary.
        * check:            Function to be called on the attachment to pre-check if decoding will work.
        * decoder:          Function to be called on the attachment to unwrap it.
        """

        def is_xml(attachment):
            # XML attachments received by mail have a 'text/plain' mimetype.
            # Therefore, if content start with '<?xml', it is considered as XML.
            is_text_plain_xml = 'text/plain' in attachment.mimetype and attachment.raw.startswith(b'<?xml')
            return attachment.mimetype.endswith('/xml') or is_text_plain_xml

        return [
            {
                'check': lambda attachment: 'pdf' in attachment.mimetype,
                'decoder': self._decode_edi_pdf,
            },
            {
                'check': is_xml,
                'decoder': self._decode_edi_xml,
            },
            {
                'check': lambda attachment: True,
                'decoder': self._decode_edi_binary,
            },
        ]

    def _unwrap_edi_attachments(self):
        """Decodes ir.attachment and unwrap sub-attachment into a sorted list of
        dictionary each representing an attachment.

        :returns:           A list of dictionary for each attachment.
        * filename:         The name of the attachment.
        * content:          The content of the attachment.
        * type:             The type of the attachment.
        * xml_tree:         The tree of the xml if type is xml.
        * pdf_reader:       The pdf_reader if type is pdf.
        * attachment:       The associated ir.attachment if any
        * sort_weight:      The associated weigth used for sorting the arrays
        """
        to_process = []

        for attachement in self:
            supported_formats = attachement._get_edi_supported_formats()
            for supported_format in supported_formats:
                if supported_format['check'](self):
                    to_process += supported_format['decoder'](attachement.name, attachement.raw)

        to_process.sort(key=lambda x: x['sort_weight'])

        return to_process

    # -------------------------------------------------------------------------
    # XSD validation
    # -------------------------------------------------------------------------

    @api.model
    def action_download_xsd_files(self):
        # To be extended by localisations, where they can download their necessary XSD files
        # Note: they should always return super().action_download_xsd_files()
        return
