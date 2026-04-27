from os.path import splitext
from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        if record._name == 'documents.document' and field_name in ('raw', 'datas', 'db_datas'):
            # Read access to document give implicit read access to the attachment
            return super()._record_to_stream(record.attachment_id.sudo(), field_name)

        return super()._record_to_stream(record, field_name)

    def _get_stream_from(
        self, record, field_name='raw', filename=None, filename_field='name', mimetype=None,
        default_mimetype='application/octet-stream',
    ):
        # skip magic detection of the file extension when it is provided
        if (record._name == 'documents.document'
            and filename is None
            and record.file_extension
        ):
            name, extension = splitext(record.name)
            if extension == f'.{record.file_extension}':
                filename = record.name
            else:
                filename = f'{name}.{record.file_extension}'

        return super()._get_stream_from(
            record, field_name, filename, filename_field, mimetype, default_mimetype)
