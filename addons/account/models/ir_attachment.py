from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools.pdf import OdooPdfFileReader, PdfReadError
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.misc import format_date

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

    @api.ondelete(at_uninstall=True)
    def _except_audit_trail(self):
        audit_trail_attachments = self.filtered(lambda attachment:
            attachment.res_model == 'account.move'
            and attachment.res_id
            and attachment.raw
            and attachment.company_id.restrictive_audit_trail
            and guess_mimetype(attachment.raw) in (
                'application/pdf',
                'application/xml',
            )
        )
        id2move = self.env['account.move'].browse(set(audit_trail_attachments.mapped('res_id'))).exists().grouped('id')
        for attachment in audit_trail_attachments:
            move = id2move.get(attachment.res_id)
            if move and move.posted_before and move.company_id.restrictive_audit_trail:
                ue = UserError(_("You cannot remove parts of a restricted audit trail."))
                ue._audit_trail = True
                raise ue

    def write(self, vals):
        if vals.keys() & {'res_id', 'res_model', 'raw', 'datas', 'store_fname', 'db_datas', 'company_id'}:
            try:
                self._except_audit_trail()
            except UserError as e:
                if (
                    not hasattr(e, '_audit_trail')
                    or vals.get('res_model') != 'documents.document'
                    or vals.keys() & {'raw', 'datas', 'store_fname', 'db_datas'}
                ):
                    raise  # do not raise if trying to version the attachment through a document
                vals.pop('res_model', None)
                vals.pop('res_id', None)
        return super().write(vals)

    def unlink(self):
        invoice_pdf_attachments = self.filtered(lambda attachment:
            attachment.res_model == 'account.move'
            and attachment.res_id
            and attachment.res_field in ('invoice_pdf_report_file', 'ubl_cii_xml_file')
            and attachment.company_id.restrictive_audit_trail
        )
        if invoice_pdf_attachments:
            # only detach the document from the field, but keep it in the database for the audit trail
            # it shouldn't be an issue as there aren't any security group on the fields as it is the public report
            invoice_pdf_attachments.res_field = False
            today = format_date(self.env, fields.Date.context_today(self))
            for attachment in invoice_pdf_attachments:
                attachment_name = attachment.name
                attachment_extension = ''
                dot_index = attachment_name.rfind('.')
                if dot_index > 0:
                    attachment_name = attachment.name[:dot_index]
                    attachment_extension = attachment.name[dot_index:]
                attachment.name = _(
                    '%(attachment_name)s (detached by %(user)s on %(date)s)%(attachment_extension)s',
                    attachment_name=attachment_name,
                    attachment_extension=attachment_extension,
                    user=self.env.user.name,
                    date=today,
                )
        return super(IrAttachment, self - invoice_pdf_attachments).unlink()

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    def _decode_edi_xml(self, filename, content):
        """Decodes an xml into a list of one dictionary representing an attachment.
        :returns:           A list with a dictionary.
        """
        try:
            xml_tree = etree.fromstring(content)
        except Exception as e:
            _logger.info('Error when reading the xml file "%s": %s', filename, e)
            return []

        to_process = []
        if xml_tree is not None:
            to_process.append({
                'attachment': self,
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
            _logger.info('Error when reading the pdf file "%s": %s', filename, e)
            return []

        # Process embedded files.
        to_process = []
        try:
            for xml_name, xml_content in pdf_reader.getAttachments():
                embedded_files = self.env['ir.attachment']._decode_edi_xml(xml_name, xml_content)
                for file_data in embedded_files:
                    file_data['sort_weight'] += 1
                    file_data['originator_pdf'] = self
                to_process.extend(embedded_files)
        except (NotImplementedError, StructError, PdfReadError) as e:
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

        * format:           Optional but helps debugging.
                            There are other methods that require the attachment
                            to be an XML other than the standard one.
        * check:            Function to be called on the attachment to pre-check if decoding will work.
        * decoder:          Function to be called on the attachment to unwrap it.
        """

        def is_xml(attachment):
            # XML attachments received by mail have a 'text/plain' mimetype (cfr. context key:
            # 'attachments_mime_plainxml'). Therefore, if content start with '<?xml', or if the filename ends with
            # '.xml', it is considered as XML.
            is_text_plain_xml = 'text/plain' in attachment.mimetype and (guess_mimetype(attachment.raw or b'').endswith('/xml') or attachment.name.endswith('.xml'))
            return attachment.mimetype.endswith('/xml') or is_text_plain_xml

        return [
            {
                'format': 'pdf',
                'check': lambda attachment: 'pdf' in attachment.mimetype,
                'decoder': self._decode_edi_pdf,
            },
            {
                'format': 'xml',
                'check': is_xml,
                'decoder': self._decode_edi_xml,
            },
            {
                'format': 'binary',
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

        for attachment in self:
            supported_formats = attachment._get_edi_supported_formats()
            for supported_format in supported_formats:
                if supported_format['check'](attachment):
                    to_process += supported_format['decoder'](attachment.name, attachment.raw)
                    break

        to_process.sort(key=lambda x: x['sort_weight'])

        return to_process

    def _post_add_create(self, **kwargs):
        move_attachments = self.filtered(lambda attachment: attachment.res_model == 'account.move')
        moves_per_id = self.env['account.move'].browse([attachment.res_id for attachment in move_attachments]).grouped('id')
        for attachment in move_attachments:
            moves_per_id[attachment.res_id]._check_and_decode_attachment(attachment)
        super()._post_add_create(**kwargs)
