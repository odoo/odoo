from odoo import models
from odoo.tools.pdf import OdooPdfFileReader, PdfReadError

import contextlib
from lxml import etree
from struct import error as StructError
import io
import logging
import zipfile

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _build_zip_from_attachments(self):
        """ Return the zip bytes content resulting from compressing the attachments in `self`"""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zipfile_obj:
            for attachment in self:
                zipfile_obj.writestr(attachment.display_name, attachment.raw)
        return buffer.getvalue()

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    def _unwrap_pdf(self, content, filename):
        """ Unwrap any embedded files that can be found in the given PDF.

        :param content: The bytes content of the PDF.
        :param filename: The filename of the PDF (used for logging).

        :return: a list of tuples (content, filename), one for each embedded file.
        """
        with io.BytesIO(content) as buffer:
            try:
                pdf_reader = OdooPdfFileReader(buffer, strict=False)
            except Exception as e:
                # Malformed pdf
                _logger.info('Error when reading the pdf file "%s": %s', filename, e)
                return []

            # Process embedded files.
            try:
                return pdf_reader.getAttachments()

            except (NotImplementedError, StructError, PdfReadError) as e:
                _logger.warning("Unable to access the attachments of %s. Tried to decrypt it, but %s.", filename, e)
                return []

    def _identify_and_unwrap_file(self, file_data):
        """ Identify the provided file and extract any sub-files.

        If the type is identified, will set the 'type' key on `file_data`.

        :param file_data: a dict representing a file to be identified and unwrapped, with the following keys:
            * filename:                  The name of the attachment.
            * content:                   The content of the attachment.
            * attachment:                The associated ir.attachment if any
            * xml_tree:                  (optional) The tree of the xml if the file is an xml.
            * root_type:                 (optional) The type of the parent file if this is a sub-file.

        :return: a list of `file_data` dicts, one for each identified/extracted file,
                 with the same keys as `file_data` and the following additional keys:
            * type:         (optional) The type of the file if identified.
            * priority:     (optional) The priority with which the file should be decoded.
        """
        # If the file is a PDF, unwrap any embedded attachments.
        if 'pdf' in file_data['attachment'].mimetype or file_data['filename'].endswith('.pdf'):
            embedded_files_data = []
            for embedded_filename, embedded_content in self._unwrap_pdf(file_data):
                embedded_file_data = {
                    'filename': embedded_filename,
                    'content': embedded_content,
                    'root_type': 'pdf',
                    'attachment': file_data['attachment'],
                }
                with contextlib.suppress(etree.ParseError):
                    embedded_file_data['xml_tree'] = etree.fromstring(embedded_content)
                embedded_files_data += self._identify_and_unwrap_file(embedded_file_data)
            return [{**file_data, 'type': 'pdf'}, *embedded_files_data]

        # If the file didn't match any known format, we just pass it on as-is.
        return [file_data]

    def _is_xml(self):
        # XML attachments received by mail have a 'text/plain' mimetype (cfr. context key:
        # 'attachments_mime_plainxml'). Therefore, if content start with '<?xml', it is considered as XML.
        return (
            self.name.endswith('.xml')
            or self.mimetype.endswith('/xml')
            or 'text/plain' in self.mimetype and (self.raw and self.raw.startswith(b'<?xml'))
        )

    def _identify_and_unwrap_edi_attachments(self):
        """ Identify and unwrap the ir.attachments in `self` into a list of dictionaries, each representing an file.

        :returns:                    A list of dictionaries for each file or sub-file.
        * filename:                  The name of the file.
        * content:                   The content of the file.
        * attachment:                The associated ir.attachment.
        * xml_tree:                  (optional) The tree of the xml if the file is an xml.
        * type:                      (optional) The type of document, if it was identified.
        * root_type:                 (optional) The type of the top-level file (if this is a sub-file) if identified.
        * priority:                  (optional) The priority with which a file should be applied on a record.
        """
        files_data = []
        for attachment in self:
            file_data = {
                'filename': attachment.name,
                'content': attachment.raw,
                'attachment': attachment,
            }

            # Optimization to already have the etree if the doc is in an XML format
            if attachment._is_xml():
                try:
                    file_data['xml_tree'] = etree.fromstring(attachment.raw)
                except etree.ParseError as e:
                    _logger.info('Error when reading the xml file "%s": %s', attachment.name, e)

            files_data += self._identify_and_unwrap_file(file_data)

        for file_data in files_data:
            if 'type' in file_data and 'root_type' not in file_data:
                file_data['root_type'] = file_data['type']

        # Sort by priority
        files_data.sort(key=lambda x: x.get('priority', 0), reverse=True)

        return files_data

    def _post_add_create(self, **kwargs):
        for move_id, attachments in self.filtered(lambda attachment: attachment.res_model == 'account.move').grouped('res_id').items():
            self.env['account.move'].browse(move_id)._extend_with_attachments(attachments)
        super()._post_add_create(**kwargs)
