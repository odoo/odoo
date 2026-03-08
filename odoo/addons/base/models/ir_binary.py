import logging
from datetime import datetime
from mimetypes import guess_extension

import werkzeug.http

from odoo import models
from odoo.exceptions import MissingError, UserError
from odoo.http import request
from odoo.http.stream import Stream
from odoo.tools import file_open, replace_exceptions
from odoo.tools.image import image_guess_size_from_field_name, image_process
from odoo.tools.mimetypes import MIMETYPE_HEAD_SIZE, get_extension, guess_mimetype
from odoo.tools.misc import verify_limited_field_access_token

DEFAULT_PLACEHOLDER_PATH = 'web/static/img/placeholder.png'
_logger = logging.getLogger(__name__)


class IrBinary(models.AbstractModel):
    _name = 'ir.binary'
    _description = "File streaming helper model for controllers"

    def _find_record(
        self,
        xmlid: str | None = None,
        res_model: str = 'ir.attachment',
        res_id: int | None = None,
        access_token: str | None = None,
        field: str | None = None,
    ) -> models.BaseModel:
        """
        Find and return a record either using an xmlid either a model+id
        pair. This method is an helper for the ``/web/content`` and
        ``/web/image`` controllers and should not be used in other
        contextes.

        :param xmlid: xmlid of the record
        :param res_model: model of the record,
            ir.attachment by default.
        :param res_id: id of the record
        :param access_token: access token to use instead
            of the access rights and access rules.
        :param field: image field name to check the access to
        :returns: single record
        :raises MissingError: when no record was found.
        """
        if xmlid:
            record = self.env.ref(xmlid, False)
        elif res_id is not None and res_model in self.env:
            record = self.env[res_model].browse(res_id).exists()
        else:
            record = None
        if not record:
            raise MissingError(f"No record found for xmlid={xmlid}, res_model={res_model}, id={res_id}")  # pylint: disable=missing-gettext
        if access_token and verify_limited_field_access_token(record, field, access_token, scope="binary"):
            return record.sudo()
        if record._can_return_content(field, access_token):
            return record.sudo()
        record.check_access("read")
        return record

    def _record_to_stream(self, record: models.BaseModel, field_name: str) -> Stream:
        """
        Low level method responsible for the actual conversion from a
        model record to a stream. This method is an extensible hook for
        other modules. It is not meant to be directly called from
        outside or the ir.binary model.

        :param record: the record where to load the data from.
        :param field_name: the binary field where to load the data
            from.
        """
        if record._name == 'ir.attachment' and field_name in ('raw', 'db_datas'):
            return record._to_http_stream()

        field = record._fields[field_name]
        record.check_field_access(field, 'read')

        if field.attachment:
            field_attachment = self.env['ir.attachment'].sudo().search(
                domain=[('res_model', '=', record._name),
                        ('res_id', '=', record.id),
                        ('res_field', '=', field_name)],
                limit=1)
            if not field_attachment:
                raise MissingError(self.env._("The related attachment does not exist."))
            return field_attachment._to_http_stream()

        return Stream.from_binary_field(record, field_name)

    def _get_stream_from(
        self,
        record,
        field_name: str = 'raw',
        filename: str | None = None,
        filename_field: str | None = 'name',
        mimetype: str | None = None,
        default_mimetype: str = 'application/octet-stream',
    ) -> Stream:
        """
        Create a :class:odoo.http.stream.Stream: from a record's binary field.

        :param record: the record where to load the data from.
        :param field_name: the binary field where to load the data from.
        :param filename: when the stream is downloaded by a browser,
            what filename it should have on disk. By default it is
            ``{model}-{id}-{field}.{extension}``, the extension is
            determined thanks to the mimetype.
        :param filename_field: like ``filename`` but use one of the
            record's char field as filename.
        :param mimetype: the data mimetype to use instead of the stored
            one (attachment) or the one determined by ``guess_mimetype``.
        :param default_mimetype: the mimetype to use when the mimetype
            couldn't be determined. By default it is
            ``application/octet-stream``.
        """
        with replace_exceptions(ValueError, by=UserError(f'Expected singleton: {record}')):  # pylint: disable=missing-gettext
            record.ensure_one()

        try:
            field_def = record._fields[field_name]
        except KeyError:
            raise UserError(f"Record has no field {field_name!r}.")  # pylint: disable=missing-gettext
        if field_def.type != 'binary':
            raise UserError(  # pylint: disable=missing-gettext
                f"Field {field_def!r} is type {field_def.type!r} but "
                f"it is only possible to stream Binary or Image fields."
            )

        stream = self._record_to_stream(record, field_name)

        if stream.type in ('data', 'path'):
            if mimetype:
                stream.mimetype = mimetype
            elif not stream.mimetype:
                if stream.type == 'data':
                    head = stream.data[:MIMETYPE_HEAD_SIZE]
                else:
                    with open(stream.path, 'rb') as file:
                        head = file.read(MIMETYPE_HEAD_SIZE)
                stream.mimetype = guess_mimetype(head, default=default_mimetype)

            if filename:
                stream.download_name = filename
            elif filename_field in record:
                stream.download_name = record[filename_field]
            if not stream.download_name:
                stream.download_name = f'{record._table}-{record.id}-{field_name}'

            stream.download_name = stream.download_name.replace('\n', '_').replace('\r', '_')
            if not get_extension(stream.download_name):
                stream.download_name += guess_extension(stream.mimetype) or ''

        return stream

    def _get_image_stream_from(
        self,
        record,
        field_name: str = 'raw',
        filename: str | None = None,
        filename_field: str | None = 'name',
        mimetype: str | None = None,
        default_mimetype: str = 'application/octet-stream',
        placeholder: str | None = None,
        width: int = 0,
        height: int = 0,
        crop: bool = False,
        quality: int = 0,
    ):
        """
        Create a :class:odoo.http.stream.Stream: from a record's binary
        field, equivalent of :meth:`~get_stream_from` but for images.

        In case the record does not exist or is not accessible, the
        alternative ``placeholder`` path is used instead. If not set,
        a path is determined via
        :meth:`~odoo.models.BaseModel._get_placeholder_filename` which
        ultimately fallbacks on ``web/static/img/placeholder.png``.

        In case the arguments ``width``, ``height``, ``crop`` or
        ``quality`` are given, the image will be post-processed and the
        ETags (the unique cache http header) will be updated
        accordingly. See also :func:`odoo.tools.image.image_process`.

        :param record: the record where to load the data from.
        :param field_name: the binary field where to load the data from.
        :param filename: when the stream is downloaded by a browser,
            what filename it should have on disk. By default it is
            ``{model}-{id}-{field}.{extension}``, the extension is
            determined thanks to the mimetype.
        :param filename_field: like ``filename`` but use one of the
            record's char field as filename.
        :param mimetype: the data mimetype to use instead of the stored
            one (attachment) or the one determined by ``guess_mimetype``.
        :param default_mimetype: the mimetype to use when the mimetype
            couldn't be determined. By default it is
            ``application/octet-stream``.
        :param placeholder: in case the image is not found or
            unaccessible, the :func:`~odoo.tools.misc.file_path` of an
            image to use instead. When not set it uses
            :meth:`models.BaseModel._get_placeholder_filename`, and
            fallbacks on using ``web/static/img/placeholder.png``.
        :param width: if not zero, the width of the resized image.
        :param height: if not zero, the height of the resized image.
        :param crop: if true, crop the image instead of rezising it.
        :param quality: if not zero, the quality of the resized image.
        """
        stream = None
        try:
            stream = self._get_stream_from(
                record=record,
                field_name=field_name,
                filename=filename,
                filename_field=filename_field,
                mimetype=mimetype,
                default_mimetype=default_mimetype,
            )
        except UserError:
            if request.params.get('download'):
                raise

        if not stream or stream.size == 0:
            if not placeholder:
                placeholder = record._get_placeholder_filename(field_name)
            stream = self._get_placeholder_stream(placeholder)

        if stream.type == 'url':
            return stream  # Rezising an external URL is not supported
        if not stream.mimetype.startswith('image/'):
            stream.mimetype = 'application/octet-stream'

        if (width, height) == (0, 0):
            width, height = image_guess_size_from_field_name(field_name)

        if isinstance(stream.etag, str):
            stream.etag += f'-{width}x{height}-crop={crop}-quality={quality}'
        if isinstance(stream.last_modified, (int, float)):
            stream.last_modified = datetime.fromtimestamp(stream.last_modified, tz=None)
        modified = werkzeug.http.is_resource_modified(
            request.httprequest.environ,
            etag=stream.etag if isinstance(stream.etag, str) else None,
            last_modified=stream.last_modified
        )

        if modified and (width or height or crop):
            if stream.type == 'path':
                with open(stream.path, 'rb') as file:
                    stream.type = 'data'
                    stream.path = None
                    stream.data = file.read()
            stream.data = image_process(
                stream.data,
                size=(width, height),
                crop=crop,
                quality=quality,
            )
            stream.size = len(stream.data)

        return stream

    def _get_placeholder_stream(self, path: str = '') -> Stream:
        if not path:
            path = DEFAULT_PLACEHOLDER_PATH
        return Stream.from_path(path, filter_ext=('.png', '.jpg'))

    def _placeholder(self, path: str = '') -> bytes:
        if not path:
            path = DEFAULT_PLACEHOLDER_PATH
        with file_open(path, 'rb', filter_ext=('.png', '.jpg')) as file:
            return file.read()
