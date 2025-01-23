import logging

from odoo import SUPERUSER_ID, api, models, _
from odoo.exceptions import RedirectWarning, UserError


_logger = logging.getLogger(__name__)


class EDIMixin(models.AbstractModel):
    _name = 'edi.mixin'
    _description = 'EDI Mixin'

    def create_document_from_attachment(self, attachment_ids):
        """Create the document records from given attachment_ids and
        redirect to respective view.

        :param list attachment_ids: List of attachments process.
        :return: An action redirecting to desired view.
        :rtype: dict
        """
        records = self._create_document_from_attachment(attachment_ids)
        return records._get_records_action(name=_("Generated Orders"))

    @api.model
    def _create_document_from_attachment(self, attachment_ids):
        """Create the document records from given attachment_ids and fill data
        by extracting detail from attachments and return generated records.

        :param list attachment_ids: List of attachments process.
        :return: Recordset.
        """
        attachments = self._fetch_attachment_records(attachment_ids)

        records = self.browse()
        for attachment in attachments:
            record = self.create({
                'partner_id': self.env.user.partner_id.id,
            })
            record._extend_with_attachments(attachment)
            records |= record
            record.message_post(attachment_ids=attachment.ids)
            attachment.write({'res_model': self._name, 'res_id': record.id})

        return records

    def _extend_with_attachments(self, attachment):
        """ Main entry point to extend/enhance record with attachment.

        :param attachment: A recordset of ir.attachment.
        :returns: None
        """
        self.ensure_one()

        file_data = attachment._unwrap_edi_attachments()[0]
        decoder = self._get_edi_decoder(file_data)
        if decoder:
            try:
                with self.env.cr.savepoint():
                    decoder(self, file_data)
            except RedirectWarning:
                raise
            except Exception:
                message = _(
                    "Error importing attachment '%(file_name)s' as order (decoder=%(decoder)s)",
                    file_name=file_data['filename'],
                    decoder=decoder.__name__,
                )
                self.with_user(SUPERUSER_ID).message_post(body=message)
                _logger.exception(message)

        if file_data.get('on_close'):
            file_data['on_close']()
        return True

    def _get_edi_decoder(self, file_data):
        """ To be extended with decoding capabilities of record data from file data.

        :returns:  Function to be later used to import the file.
                   Function' args:
                   - record
                   - file_data: attachemnt information / value
                   returns True if was able to process the order
        """
        if file_data['type'] in ('pdf', 'binary'):
            return lambda *args: False
        if file_data['type'] == 'xml':
            ubl_cii_xml_builder = self._get_record_ubl_builder_from_xml_tree(file_data['xml_tree'])
            if ubl_cii_xml_builder is not None:
                return ubl_cii_xml_builder._import_order_ubl
        return

    def _fetch_attachment_records(self, attachment_ids):
        """Retrieve and validate attachments.

        :param list attachment_ids: List of attachment IDs to process.
        :return: Recordset of validated attachments.
        :rtype: ir.attachment
        """
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        if not attachments:
            raise UserError(_("No attachment was provided"))
        return attachments

    def _get_edi_builders(self):
        return []
