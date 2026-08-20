from __future__ import annotations

import base64
import functools
import typing
import warnings
from operator import attrgetter

import psycopg2

from odoo.exceptions import UserError
from odoo.tools import SQL
from odoo.tools.binary import EMPTY_BINARY, BinaryBytes, BinaryValue

from .fields import Field
from .utils import parse_field_expr

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

    def update_db(self, model, columns):
        if self.column_type is None:
            if self.default and model.env.execute_query(SQL('SELECT 1 FROM %s LIMIT 1', SQL.identifier(model._table))):
                model.pool.post_init(self.update_db_binary_attachment, model)
            return False
        return super().update_db(model, columns)

    def update_db_binary_attachment(self, model):
        """Initialized the records for binary fields stored as attachment with the default"""
        value = self.default(model)
        # assume already initialized when some records have a value
        if not value or model.search_count([(self.name, '!=', False)], limit=1):
            return
        model.search([(self.name, '=', False)]).write({self.name: value})

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

    def convert_to_cache(self, value, records, validate=True) -> BinaryValue | None:
        if not value:
            return None
        if isinstance(value, BinaryValue):
            return value
        if isinstance(value, str):
            # a string may come from RPC, it is base64 encoded
            decoded_value = base64.b64decode(value, validate=validate)
            return BinaryBytes(decoded_value)
        if isinstance(value, dict):
            # {filename, content}
            if 'content' not in value:
                if len(records) == 1 and 'filename' in value:
                    # we support changing only the file name when the content
                    # can be read from the record
                    return BinaryBytes(records[self.name].content, filename=value['filename'])
                raise ValueError(f"{self}: missing 'content' when writing a dict")
            filename = value.get('filename') or ''
            binary_value = self.convert_to_cache(value['content'], records)
            if filename and binary_value.filename != filename:
                binary_value = BinaryBytes(binary_value.content, filename=filename)
            return binary_value
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
        filename = value.filename
        res = {
            'filename': filename,
            'content': value.to_base64(),
            'size': value.size,
        }
        if not filename or filename == self.name:  # remove empty name
            res.pop('filename')
        return res

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
            if cache_value:
                # update the existing attachments
                atts.write({'raw': cache_value})
                atts_records = records.browse(atts.mapped('res_id'))
                # create the missing attachments
                missing = (real_records - atts_records)
                if missing:
                    atts.create([{
                            'res_model': record._name,
                            'res_field': self.name,
                            'res_id': record.id,
                            'type': 'binary',
                            'raw': cache_value,
                        }
                        for record in missing
                    ])
            else:
                atts.unlink()

    def expression_getter(self, field_expr):
        get_value = self.__get__
        _fname, property_name = parse_field_expr(field_expr)
        if property_name == 'size':
            return lambda record: get_value(record).size
        if property_name == 'filename':
            return lambda record: get_value(record).filename
        return super().expression_getter(field_expr)

    def to_sql(self, table):
        if self.attachment and self.store and not self.compute and not self.compute_sql:
            Attachment = table._model.sudo().env['ir.attachment']
            alias = table._make_alias(self.name, Attachment)
            table._query.add_join('LEFT JOIN', alias, SQL("""(
                SELECT DISTINCT (res_id) res_id, file_size, name, id
                FROM ir_attachment
                WHERE res_model = %s AND res_field = %s AND res_id IS NOT NULL
                ORDER BY res_id, id
            )""", self.model_name, self.name), SQL("%s = %s", alias.res_id, table.id, to_flush=self))
            return alias.id  # dummy value
        return super().to_sql(table)

    def property_to_sql(self, field_sql, property_name):
        if self.attachment:
            Attachment = field_sql._table._model.sudo().env['ir.attachment']
            alias = field_sql._table._make_alias(self.name, Attachment)
            if property_name == 'size':
                return SQL("COALESCE(%s, 0)", alias.file_size)
            if property_name == 'filename':
                return SQL("COALESCE(NULLIF(%s, %s), '')", alias.name, self.name)
        else:
            if property_name == 'size':
                return SQL("COALESCE(octet_length(%s), 0)", field_sql)
            if property_name == 'filename':
                return SQL("''::varchar")
        return super().property_to_sql(field_sql, property_name)

    def condition_to_sql(self, table: TableSQL, field_expr: str, operator: str, value) -> SQL:
        if field_expr != self.name or (not self.attachment and operator in ('in', 'not in') and set(value) == {False}):
            return super().condition_to_sql(table, field_expr, operator, value)
        if self.attachment and operator in ('in', 'not in') and set(value) == {False}:
            return SQL(
                "%sEXISTS (SELECT 1 FROM ir_attachment WHERE res_model = %s AND res_field = %s AND res_id = %s)",
                SQL("NOT ") if operator == 'in' else SQL(),
                table._model._name,
                self.name,
                table.id,
            )
        raise ValueError('Binary field, accepts only existence check; skipping domain')


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
        if not self._setup_done and not model._abstract and not model._log_access:
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
        if self.readonly and (
            (not self.max_width and not self.max_height)
            or (
                isinstance(self.related_field, Image)
                and self.max_width == self.related_field.max_width
                and self.max_height == self.related_field.max_height
            )
        ):
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
    def filename(self) -> str:
        self._check_concurrent_modification()
        name = self.__attachment.name or ''
        field_name = self.__attachment.res_field
        return name if name != field_name else ''

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

    @property
    def checksum(self):
        return self.__checksum

    def open(self):
        self._check_concurrent_modification()
        return self.__attachment.raw.open()

    def __repr__(self):
        return f"BinaryValueAttachment(id={self.__attachment.id})"
