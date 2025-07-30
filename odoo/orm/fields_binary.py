from __future__ import annotations

import base64
import binascii
import contextlib
import itertools
import reprlib
import typing
import warnings
from operator import attrgetter

import psycopg2

from odoo.exceptions import CacheMiss, UserError
from odoo.tools import SQL, human_size, image_process, lazy_property
from odoo.tools.mimetypes import guess_mimetype

from .fields import Field, _logger
from .utils import SQL_OPERATORS

if typing.TYPE_CHECKING:
    from odoo.tools import Query

    from .models import BaseModel

# http://initd.org/psycopg/docs/usage.html#binary-adaptation
# Received data is returned as buffer (in Python 2) or memoryview (in Python 3).
_BINARY = memoryview


class Binary(Field):
    """Encapsulates a binary content (e.g. a file).

    :param bool attachment: whether the field should be stored as `ir_attachment`
        or in a column of the model's table (default: ``True``).
    """
    type = 'binary'

    prefetch = False                    # not prefetched by default
    _depends_context = ('bin_size',)    # depends on context (content or size)
    attachment = True                   # whether value is stored in attachment

    @lazy_property
    def column_type(self):
        return None if self.attachment else ('bytea', 'bytea')

    def _get_attrs(self, model_class, name):
        attrs = super()._get_attrs(model_class, name)
        if not attrs.get('store', True):
            attrs['attachment'] = False
        return attrs

    _description_attachment = property(attrgetter('attachment'))

    def convert_to_column(self, value, record, values=None, validate=True):
        # Binary values may be byte strings (python 2.6 byte array), but
        # the legacy OpenERP convention is to transfer and store binaries
        # as base64-encoded strings. The base64 string may be provided as a
        # unicode in some circumstances, hence the str() cast here.
        # This str() coercion will only work for pure ASCII unicode strings,
        # on purpose - non base64 data must be passed as a 8bit byte strings.
        if not value:
            return None
        # Detect if the binary content is an SVG for restricting its upload
        # only to system users.
        magic_bytes = {
            b'P',  # first 6 bits of '<' (0x3C) b64 encoded
            b'<',  # plaintext XML tag opening
        }
        if isinstance(value, str):
            value = value.encode()
        if validate and value[:1] in magic_bytes:
            try:
                decoded_value = base64.b64decode(value.translate(None, delete=b'\r\n'), validate=True)
            except binascii.Error:
                decoded_value = value
            # Full mimetype detection
            if (guess_mimetype(decoded_value).startswith('image/svg') and
                    not record.env.is_system()):
                raise UserError(record.env._("Only admins can upload SVG files."))
        if isinstance(value, bytes):
            return psycopg2.Binary(value)
        try:
            return psycopg2.Binary(str(value).encode('ascii'))
        except UnicodeEncodeError:
            raise UserError(record.env._("ASCII characters are required for %(value)s in %(field)s", value=value, field=self.name))

    def convert_to_cache(self, value, record, validate=True):
        if isinstance(value, _BINARY):
            return bytes(value)
        if isinstance(value, str):
            # the cache must contain bytes or memoryview, but sometimes a string
            # is given when assigning a binary field (test `TestFileSeparator`)
            return value.encode()
        if isinstance(value, int) and \
                (record._context.get('bin_size') or
                 record._context.get('bin_size_' + self.name)):
            # If the client requests only the size of the field, we return that
            # instead of the content. Presumably a separate request will be done
            # to read the actual content, if necessary.
            value = human_size(value)
            # human_size can return False (-> None) or a string (-> encoded)
            return value.encode() if value else None
        return None if value is False else value

    def convert_to_record(self, value, record):
        if isinstance(value, _BINARY):
            return bytes(value)
        return False if value is None else value

    def compute_value(self, records):
        bin_size_name = 'bin_size_' + self.name
        if records.env.context.get('bin_size') or records.env.context.get(bin_size_name):
            # always compute without bin_size
            records_no_bin_size = records.with_context(**{'bin_size': False, bin_size_name: False})
            super().compute_value(records_no_bin_size)
            # manually update the bin_size cache
            cache = records.env.cache
            for record_no_bin_size, record in zip(records_no_bin_size, records):
                try:
                    value = cache.get(record_no_bin_size, self)
                    # don't decode non-attachments to be consistent with pg_size_pretty
                    if not (self.store and self.column_type):
                        with contextlib.suppress(TypeError, binascii.Error):
                            value = base64.b64decode(value)
                    try:
                        if isinstance(value, (bytes, _BINARY)):
                            value = human_size(len(value))
                    except (TypeError):
                        pass
                    cache_value = self.convert_to_cache(value, record)
                    # the dirty flag is independent from this assignment
                    cache.set(record, self, cache_value, check_dirty=False)
                except CacheMiss:
                    pass
        else:
            super().compute_value(records)

    def read(self, records):
        def _encode(s: str | bool) -> bytes | bool:
            if isinstance(s, str):
                return s.encode("utf-8")
            return s

        # values are stored in attachments, retrieve them
        assert self.attachment
        domain = [
            ('res_model', '=', records._name),
            ('res_field', '=', self.name),
            ('res_id', 'in', records.ids),
        ]
        bin_size = records.env.context.get('bin_size')
        data = {
            att.res_id: _encode(human_size(att.file_size)) if bin_size else att.datas
            for att in records.env['ir.attachment'].sudo().search(domain)
        }
        records.env.cache.insert_missing(records, self, map(data.get, records._ids))

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
                'datas': value,
            }
            for record, value in record_values
            if value
        ])

    def write(self, records, value):
        records = records.with_context(bin_size=False)
        if not self.attachment:
            super().write(records, value)
            return

        # discard recomputation of self on records
        records.env.remove_to_compute(self, records)

        # update the cache, and discard the records that are not modified
        cache = records.env.cache
        cache_value = self.convert_to_cache(value, records)
        records = cache.get_records_different_from(records, self, cache_value)
        if not records:
            return
        if self.store:
            # determine records that are known to be not null
            not_null = cache.get_records_different_from(records, self, None)

        cache.update(records, self, itertools.repeat(cache_value))

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
                atts.write({'datas': value})
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
                            'datas': value,
                        }
                        for record in missing
                    ])
            else:
                atts.unlink()

    def condition_to_sql(self, field_expr: str, operator: str, value, model: BaseModel, alias: str, query: Query) -> SQL:
        if not self.attachment or field_expr != self.name:
            return super().condition_to_sql(field_expr, operator, value, model, alias, query)
        # check permission
        model._check_field_access(self, 'read')
        assert (operator in ('in', 'not in') and set(value) == {False}) or (operator in ('=', '!=') and not value), "Should have been done in Domain optimization"
        return SQL(
            "%s%s(SELECT res_id FROM ir_attachment WHERE res_model = %s AND res_field = %s)",
            model._field_to_sql(alias, 'id', query),
            SQL_OPERATORS['not in' if operator in ('in', '=') else 'in'],
            model._name,
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
            record.env.cache.update(record, self, itertools.repeat(cache_value))
        super(Image, self).create(new_record_values)

    def write(self, records, value):
        try:
            new_value = self._image_process(value, records.env)
        except UserError:
            if not any(records._ids):
                # Some crap is assigned to a new record. This can happen in an
                # onchange, where the client sends the "bin size" value of the
                # field instead of its full value (this saves bandwidth). In
                # this case, we simply don't assign the field: its value will be
                # taken from the records' origin.
                return
            raise

        super(Image, self).write(records, new_value)
        cache_value = self.convert_to_cache(value if self.related else new_value, records)
        dirty = self.column_type and self.store and any(records._ids)
        records.env.cache.update(records, self, itertools.repeat(cache_value), dirty=dirty)

    def _inverse_related(self, records):
        super()._inverse_related(records)
        if not (self.max_width and self.max_height):
            return
        # the inverse has been applied with the original image; now we fix the
        # cache with the resized value
        for record in records:
            value = self._process_related(record[self.name], record.env)
            record.env.cache.set(record, self, value, dirty=(self.store and self.column_type))

    def _image_process(self, value, env):
        if self.readonly and not self.max_width and not self.max_height:
            # no need to process images for computed fields, or related fields
            return value
        try:
            img = base64.b64decode(value or '') or False
        except:
            raise UserError(env._("Image is not encoded in base64."))

        if img and guess_mimetype(img, '') == 'image/webp':
            if not self.max_width and not self.max_height:
                return value
            # Fetch resized version.
            Attachment = env['ir.attachment']
            checksum = Attachment._compute_checksum(img)
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
                    return resized.datas or value
            return value

        return base64.b64encode(image_process(img,
            size=(self.max_width, self.max_height),
            verify_resolution=self.verify_resolution,
        ) or b'') or False

    def _process_related(self, value, env):
        """Override to resize the related value before saving it on self."""
        try:
            return self._image_process(super()._process_related(value, env), env)
        except UserError:
            # Avoid the following `write` to fail if the related image was saved
            # invalid, which can happen for pre-existing databases.
            return False
