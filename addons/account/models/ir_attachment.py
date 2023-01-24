# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.tools.pdf import OdooPdfFileReader

from lxml import etree
import io
import logging
import pathlib

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
        * filename:         The name of the attachment.
        * content:          The content of the attachment.
        * type:             The type of the attachment.
        * xml_tree:         The tree of the xml if type is xml.
        """
        self.ensure_one()
        try:
            xml_tree = etree.fromstring(content)
        except Exception as e:
            _logger.exception("Error when converting the xml content to etree: %s" % e)
            return []

        to_process = []
        if len(xml_tree):
            to_process.append({
                'filename': filename,
                'content': content,
                'type': 'xml',
                'xml_tree': xml_tree,
            })
        return to_process

    @api.model
    def _decode_edi_pdf(self, filename, content):
        """Decodes a pdf and unwrap sub-attachment into a list of dictionary each representing an attachment.

        :returns:           A list of dictionary for each attachment.
        * filename:         The name of the attachment.
        * content:          The content of the attachment.
        * type:             The type of the attachment.
        * xml_tree:         The tree of the xml if type is xml.
        * pdf_reader:       The pdf_reader if type is pdf.
        """
        try:
            buffer = io.BytesIO(content)
            pdf_reader = OdooPdfFileReader(buffer, strict=False)
        except Exception as e:
            # Malformed pdf
            _logger.exception("Error when reading the pdf: %s" % e)
            return []

        # Process embedded files.
        to_process = []
        try:
            for xml_name, xml_content in pdf_reader.getAttachments():
                to_process.extend(self._decode_edi_xml(xml_name, xml_content))
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

    @api.model
    def _decode_edi_binary(self, filename, content):
        """Decodes any file into a list of one dictionary representing an attachment.
        This is a fallback for all files that are not decoded by other methods.

        :returns:           A list with a dictionary.
        * filename:         The name of the attachment.
        * content:          The content of the attachment.
        * type:             The type of the attachment.
        """
        return [{
            'filename': filename,
            'extension': ''.join(pathlib.Path(filename).suffixes),
            'content': content,
            'type': 'binary',
        }]

    def _decode_edi_attachment(self):
        """Decodes an ir.attachment and unwrap sub-attachment into a list of dictionary each representing an attachment.

        :returns:           A list of dictionary for each attachment.
        * filename:         The name of the attachment.
        * content:          The content of the attachment.
        * type:             The type of the attachment.
        * xml_tree:         The tree of the xml if type is xml.
        * pdf_reader:       The pdf_reader if type is pdf.
        """
        self.ensure_one()

        # XML attachments received by mail have a 'text/plain' mimetype.
        # Therefore, if content start with '<?xml', it is considered as XML.
        to_process = []
        is_text_plain_xml = 'text/plain' in self.mimetype and self.raw.startswith(b'<?xml')
        if 'pdf' in self.mimetype:
            to_process.extend({**self._decode_edi_pdf(), 'attachment': self})
        elif 'xml' in self.mimetype or is_text_plain_xml:
            to_process.extend({**self._decode_edi_xml(), 'attachment': self})
        else:
            to_process.extend({**self._decode_edi_binary(), 'attachment': self})

        sort_map = {
            'xml': 10,
            'pdf': 20,
            'binary': 30,
        }
        to_process.sort(key=lambda x: sort_map.get(x['type'], 99999))

        return to_process
