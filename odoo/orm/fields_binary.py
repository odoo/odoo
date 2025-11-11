from __future__ import annotations

import base64
import functools
import typing
import warnings
from operator import attrgetter

import psycopg2

from odoo.exceptions import UserError
from odoo.tools import SQL, human_size
from odoo.tools.binary import EMPTY_BINARY, BinaryBytes, BinaryValue

from .fields import Field
from .utils import SQL_OPERATORS

if typing.TYPE_CHECKING:
    from .environments import Environment
    from .query import TableSQL
    from odoo.addons.base.models.ir_attachment import IrAttachment

# http://initd.org/psycopg/docs/usage.html#binary-adaptation
# Received data is returned as `memoryview`.


class Binary(Field[BinaryValue]):
    """Encapsulates a binary content (e.g. a file).

    :param bool attachment: whether the field should be stored as `ir_attachment`
        or in a column of the model's table (default: ``True``).
    """
    type = 'binary'

    prefetch = False                    # not prefetched by default
    attachment = True                   # whether value is stored in attachment

    @functools.cached_property
    def column_type(self):
        return None if self.attachment else ('bytea', 'bytea')

    def _get_attrs(self, model_class, name):
        attrs = super()._get_attrs(model_class, name)
        if not attrs.get('store', True):
            attrs['attachment'] = False
        return attrs

    _description_attachment = property(attrgetter('attachment'))

    def _description_groupable(self, env):
        return False

    def _description_sortable(self, env):
        return False

    def convert_to_column(self, value, record, values=None, validate=True):
        data = self.convert_to_cache(value, record, validate) or EMPTY_BINARY
        value = data.content
        if not value:
            return None
        # Detect if the binary content is an SVG for restricting its upload
        # only to system users. Check plaintext XML tag opening.
        if validate and value[:1] == b'<':
            # Full mimetype detection
            if (data.mimetype.startswith('image/svg') and
                    not record.env.is_system()):
                raise UserError(record.env._("Only admins can upload SVG files."))
        return psycopg2.Binary(value)

    def convert_to_cache(self, value, record, validate=True) -> BinaryValue | None:
        if not value:
            return None
        if isinstance(value, BinaryValue):
            return value
        if isinstance(value, str):
            # a string may come from RPC, it is base64 encoded
            decoded_value = base64.b64decode(value, validate=validate)
            return BinaryBytes(decoded_value)
        # Error needed because we used to write base64 encoded data and we
        # cannot distinguish whether bytes are encoded or not in base64.
        if isinstance(value, bytes) and (self.related_field or self).name == 'raw':
            # Exception for the raw field, we know bytes are raw.
            return BinaryBytes(value)
        raise TypeError(f'{self}: use BinaryValue instead of {value.__class__.__name__}')

    def _insert_cache(self, records, values):
        # values are retrieved as a memoryview from the database
        values = [BinaryBytes(v) if v else None for v in values]
        return super()._insert_cache(records, values)

    def _update_cache(self, records, cache_value, dirty=False):
        if cache_value is not None:
            assert isinstance(cache_value, BinaryValue), f"{self}: unexpected type {type(cache_value)}"
            cache_value.size  # check if exists and raise if we have issues
        return super()._update_cache(records, cache_value, dirty)

    def convert_to_record(self, value, record):
        return value or EMPTY_BINARY

    def convert_to_write(self, value, record):
        return self.convert_to_cache(value, record, validate=False) or False

    def convert_to_read(self, value, record, use_display_name=True):
        if not value:
            return False
        value = self.convert_to_cache(value, record, validate=False)
        if (
            record.env.context.get('bin_size')
            or record.env.context.get('bin_size_' + self.name)
        ):
            # TODO js detects that value looks like a size otherwise it
            # supposes that this is base64 encoded and requests the image
            return human_size(value.size)
        # we read bytes in base64 format for RPC
        if (self.related_field or self).name == 'datas':
            return value.decode(encoding='ascii')
        return value.to_base64()

    def read(self, records):
        # values are stored in attachments, retrieve them
        assert self.attachment
        domain = [
            ('res_model', '=', records._name),
            ('res_field', '=', self.name),
            ('res_id', 'in', records.ids),
        ]
        data = {
            att.res_id: BinaryValueAttachment(att)
            for att in records.env['ir.attachment'].sudo().search_fetch(domain)
        }
        super()._insert_cache(records, map(data.get, records._ids))

    def create(self, record_values):
        assert self.attachment
        if not record_values:
            return
        # create the attachments that store the values
        env = record_values[0][0].env
        env['ir.attachment'].sudo().create([
            {
                'name': self.name,
                'res_model': self.model_name,
                'res_field': self.name,
                'res_id': record.id,
                'type': 'binary',
                'raw': value,
            }
            for record, value in record_values
            if value
        ])

    def write(self, records, value):
        if not self.attachment:
            super().write(records, value)
            return

        # discard recomputation of self on records
        records.env.remove_to_compute(self, records)

        # update the cache, and discard the records that are not modified
        cache_value = self.convert_to_cache(value, records)
        records = self._filter_not_equal(records, cache_value)
        if not records:
            return
        if self.store:
            # determine records that are known to be not null
            not_null = self._filter_not_equal(records, None)

        self._update_cache(records, cache_value)

        # retrieve the attachments that store the values, and adapt them
        if self.store and any(records._ids):
            real_records = records.filtered('id')
            atts = records.env['ir.attachment'].sudo()
            if not_null:
                atts = atts.search([
                    ('res_model', '=', self.model_name),
                    ('res_field', '=', self.name),
                    ('res_id', 'in', real_records.ids),
                ])
            if value:
                # update the existing attachments
                atts.write({'raw': value})
                atts_records = records.browse(atts.mapped('res_id'))
                # create the missing attachments
                missing = (real_records - atts_records)
                if missing:
                    atts.create([{
                            'name': self.name,
                            'res_model': record._name,
                            'res_field': self.name,
                            'res_id': record.id,
                            'type': 'binary',
                            'raw': value,
                        }
                        for record in missing
                    ])
            else:
                atts.unlink()

    def condition_to_sql(self, table: TableSQL, field_expr: str, operator: str, value) -> SQL:
        if not self.attachment or field_expr != self.name:
            return super().condition_to_sql(table, field_expr, operator, value)
        assert operator in ('in', 'not in') and set(value) == {False}, "Should have been done in Domain optimization"
        return SQL(
            "%s%s(SELECT res_id FROM ir_attachment WHERE res_model = %s AND res_field = %s)",
            table.id,
            SQL_OPERATORS['not in' if operator in ('in', '=') else 'in'],
            table._model._name,
            self.name,
        )


class Image(Binary):
    """Encapsulates an image, extending :class:`Binary`.

    If image size is greater than the ``max_width``/``max_height`` limit of pixels, the image will be
    resized to the limit by keeping aspect ratio.

    :param int max_width: the maximum width of the image (default: ``0``, no limit)
    :param int max_height: the maximum height of the image (default: ``0``, no limit)
    :param bool verify_resolution: whether the image resolution should be verified
        to ensure it doesn't go over the maximum image resolution (default: ``True``).
        See :class:`odoo.tools.image.ImageProcess` for maximum image resolution (default: ``50e6``).

    .. note::

        If no ``max_width``/``max_height`` is specified (or is set to 0) and ``verify_resolution`` is False,
        the field content won't be verified at all and a :class:`Binary` field should be used.
    """
    max_width = 0
    max_height = 0
    verify_resolution = True

    def setup(self, model):
        super().setup(model)
        if not model._abstract and not model._log_access:
            warnings.warn(f"Image field {self} requires the model to have _log_access = True", stacklevel=1)

    def create(self, record_values):
        new_record_values = []
        for record, value in record_values:
            new_value = self._image_process(value, record.env)
            new_record_values.append((record, new_value))
            # when setting related image field, keep the unprocessed image in
            # cache to let the inverse method use the original image; the image
            # will be resized once the inverse has been applied
            cache_value = self.convert_to_cache(value if self.related else new_value, record)
            self._update_cache(record, cache_value)
        super().create(new_record_values)

    def write(self, records, value):
        try:
            new_value = self._image_process(value, records.env)
        except (UserError, TypeError, ValueError):
            if not any(records._ids):
                # Some crap is assigned to a new record. This can happen in an
                # onchange, where the client sends the "bin size" value of the
                # field instead of its full value (this saves bandwidth). In
                # this case, we simply don't assign the field: its value will be
                # taken from the records' origin.
                return
            raise

        super().write(records, new_value)
        cache_value = self.convert_to_cache(value if self.related else new_value, records)
        self._update_cache(records, cache_value, dirty=True)

    def _inverse_related(self, records):
        super()._inverse_related(records)
        if not (self.max_width and self.max_height):
            return
        # the inverse has been applied with the original image; now we fix the
        # cache with the resized value
        for record in records:
            value = self._process_related(record[self.name], record.env) or None
            self._update_cache(record, value, dirty=True)

    def _image_process(self, value, env: Environment) -> BinaryValue | typing.Literal[False]:
        if self.readonly and not self.max_width and not self.max_height:
            # no need to process images for computed fields, or related fields
            return value
        data = self.convert_to_cache(value, env[self.model_name])
        img = data.content if data else b''

        if data and data.mimetype == 'image/webp':
            if not self.max_width and not self.max_height:
                return data
            # Fetch resized version.
            Attachment = env['ir.attachment']
            checksum = Attachment._compute_checksum(data)
            origins = Attachment.search([
                ['id', '!=', False],  # No implicit condition on res_field.
                ['checksum', '=', checksum],
            ])
            if origins:
                origin_ids = [attachment.id for attachment in origins]
                resized_domain = [
                    ['id', '!=', False],  # No implicit condition on res_field.
                    ['res_model', '=', 'ir.attachment'],
                    ['res_id', 'in', origin_ids],
                    ['description', '=', 'resize: %s' % max(self.max_width, self.max_height)],
                ]
                resized = Attachment.sudo().search(resized_domain, limit=1)
                if resized:
                    # Fallback on non-resized image (value).
                    return resized.raw or data
            return data

        # delay import of image_process until this point
        from odoo.tools.image import image_process  # noqa: PLC0415
        return BinaryBytes(image_process(img,
            size=(self.max_width, self.max_height),
            verify_resolution=self.verify_resolution,
        )) or False

    def _process_related(self, value, env):
        """Override to resize the related value before saving it on self."""
        try:
            return self._image_process(super()._process_related(value, env), env)
        except UserError:
            # Avoid the following `write` to fail if the related image was saved
            # invalid, which can happen for pre-existing databases.
            return False


class BinaryValueAttachment(BinaryValue):
    """Lazy BinaryValue that uses an attachment's ``raw`` field as contents.

    A Binary field that stores the data in attachment's will use this class in
    its cache. Once we request the content, the `raw` field will be computed and
    will return another BinaryValue.
    """
    __slots__ = ('__attachment', '__checksum')

    def __init__(self, attachment: IrAttachment):
        assert attachment.env.su and attachment._name == 'ir.attachment' and len(attachment) == 1
        self.__attachment = attachment
        self.__checksum = attachment.checksum

    def _check_concurrent_modification(self):
        assert self.__checksum == self.__attachment.checksum, "Attachment modified when accessing it from a Binary field"

    @property
    def content(self) -> bytes:
        self._check_concurrent_modification()
        return self.__attachment.raw.content

    @property
    def mimetype(self) -> str:
        self._check_concurrent_modification()
        return self.__attachment.mimetype

    @property
    def size(self) -> int:
        self._check_concurrent_modification()
        # get from the attachment
        # if we don't have a size, read raw to be consistent
        return self.__attachment.file_size or super().size

    def open(self):
        self._check_concurrent_modification()
        return self.__attachment.raw.open()

    def __repr__(self):
        return f"BinaryAttachment(id={self.__attachment.id})"
