# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=method-required-super
import base64
import itertools
import mimetypes
import os.path
from io import BytesIO, IOBase

from odoo import fields
from odoo.tools.mimetypes import guess_mimetype

from odoo.addons.fs_attachment.models.ir_attachment import IrAttachment


class FSFileValue:
    def __init__(
        self,
        attachment: IrAttachment = None,
        name: str = None,
        value: bytes | IOBase = None,
    ) -> None:
        """
        This class holds the information related to FSFile field. It can be
        used to assign a value to a FSFile field. In such a case, you can pass
        the name and the file content as parameters.

        When

        :param attachment: the attachment to use to store the file.
        :param name: the name of the file. If not provided, the name will be
            taken from the attachment or the io.IOBase.
        :param value: the content of the file. It can be bytes or an io.IOBase.
        """
        self._is_new: bool = attachment is None
        self._buffer: IOBase = None
        self._attachment: IrAttachment = attachment
        if name and attachment:
            raise ValueError("Cannot set name and attachment at the same time")
        if value:
            if isinstance(value, IOBase):
                self._buffer = value
                if not hasattr(value, "name"):
                    if name:
                        self._buffer.name = name
                    else:
                        raise ValueError(
                            "name must be set when value is an io.IOBase "
                            "and is not provided by the io.IOBase"
                        )
            elif isinstance(value, bytes):
                self._buffer = BytesIO(value)
                if not name:
                    raise ValueError("name must be set when value is bytes")
                self._buffer.name = name
            else:
                raise ValueError("value must be bytes or io.BytesIO")
        elif name:
            self._buffer = BytesIO(b"")
            self._buffer.name = name

    @property
    def write_buffer(self) -> BytesIO:
        if self._buffer is None:
            name = self._attachment.name if self._attachment else None
            self._buffer = BytesIO()
            self._buffer.name = name
        return self._buffer

    @property
    def name(self) -> str | None:
        name = (
            self._attachment.name
            if self._attachment
            else self._buffer.name
            if self._buffer
            else None
        )
        if name:
            return os.path.basename(name)
        return None

    @name.setter
    def name(self, value: str) -> None:
        # the name should only be updatable while the file is not yet stored
        # TODO, we could also allow to update the name of the file and rename
        # the file in the external file system
        if self._is_new:
            self.write_buffer.name = value
        else:
            raise ValueError(
                "The name of the file can only be updated while the file is not "
                "yet stored"
            )

    @property
    def is_new(self) -> bool:
        return self._is_new

    @property
    def mimetype(self) -> str | None:
        """Return the mimetype of the file.

        If an attachment is set, the mimetype is taken from the attachment.
        If no attachment is set, the mimetype is guessed from the name of the
        file.
        If no name is set or if the mimetype cannot be guessed from the name,
        the mimetype is guessed from the content of the file.
        """
        mimetype = None
        if self._attachment:
            mimetype = self._attachment.mimetype
        elif self.name:
            mimetype = mimetypes.guess_type(self.name)[0]
        # at last, try to guess the mimetype from the content
        return mimetype or guess_mimetype(self.getvalue())

    @property
    def size(self) -> int:
        if self._attachment:
            return self._attachment.file_size
        # check if the object supports len
        try:
            return len(self._buffer)
        except TypeError:  # pylint: disable=except-pass
            # the object does not support len
            pass
        # if we are on a BytesIO, we can get the size from the buffer
        if isinstance(self._buffer, BytesIO):
            return self._buffer.getbuffer().nbytes
        # we cannot get the size
        return 0

    @property
    def url(self) -> str | None:
        return self._attachment.fs_url or None if self._attachment else None

    @property
    def internal_url(self) -> str | None:
        return self._attachment.internal_url or None if self._attachment else None

    @property
    def url_path(self) -> str | None:
        return self._attachment.fs_url_path or None if self._attachment else None

    @property
    def attachment(self) -> IrAttachment | None:
        return self._attachment

    @attachment.setter
    def attachment(self, value: IrAttachment) -> None:
        self._attachment = value
        self._buffer = None

    @property
    def extension(self) -> str | None:
        # get extension from mimetype
        ext = os.path.splitext(self.name)[1]
        if not ext:
            ext = mimetypes.guess_extension(self.mimetype)
            ext = ext and ext[1:]
        return ext

    @property
    def read_buffer(self) -> BytesIO:
        if self._buffer is None:
            content = b""
            name = None
            if self._attachment:
                content = self._attachment.raw or b""
                name = self._attachment.name
            self._buffer = BytesIO(content)
            self._buffer.name = name
        return self._buffer

    def getvalue(self) -> bytes:
        buffer = self.read_buffer
        current_pos = buffer.tell()
        buffer.seek(0)
        value = buffer.read()
        buffer.seek(current_pos)
        return value

    def open(
        self,
        mode="rb",
        block_size=None,
        cache_options=None,
        compression=None,
        new_version=True,
        **kwargs,
    ) -> IOBase:
        """
        Return a file-like object that can be used to read and write the file content.
        See the documentation of open() into the ir.attachment model from the
        fs_attachment module for more information.
        """
        if not self._attachment:
            raise ValueError("Cannot open a file that is not stored")
        return self._attachment.open(
            mode=mode,
            block_size=block_size,
            cache_options=cache_options,
            compression=compression,
            new_version=new_version,
            **kwargs,
        )


class FSFile(fields.Binary):
    """
    This field is a binary field that stores the file content in an external
    filesystem storage referenced by a storage code.

    A major difference with the standard Odoo binary field is that the value
    is not encoded in base64 but is a bytes object.

    Moreover, the field is designed to always return an instance of
    :class:`FSFileValue` when reading the value. This class is a file-like
    object that can be used to read the file content and to get information
    about the file (filename, mimetype, url, ...).

    To update the value of the field, the following values are accepted:

    - a bytes object (e.g. ``b"..."``)
    - a dict with the following keys:
      - ``filename``: the filename of the file
      - ``content``: the content of the file encoded in base64
    - a FSFileValue instance
    - a file-like object (e.g. an instance of :class:`io.BytesIO`)

    When the value is provided is a bytes object the filename is set to the
    name of the field. You can override this behavior by providing specifying
    a fs_filename key in the context. For example:

    .. code-block:: python

        record.with_context(fs_filename='my_file.txt').write({
            'field': b'...',
        })

    The same applies when the value is provided as a file-like object but the
    filename is set to the name of the file-like object or not a property of
    the file-like object. (e.g. ``io.BytesIO(b'...')``).


    When the value is converted to the read format, it's always an instance of
    dict with the following keys:

    - ``filename``: the filename of the file
    - ``mimetype``: the mimetype of the file
    - ``size``: the size of the file
    - ``url``: the url to access the file

    """

    type = "fs_file"

    attachment: bool = True

    def __init__(self, *args, **kwargs):
        kwargs["attachment"] = True
        super().__init__(*args, **kwargs)

    def read(self, records):
        domain = [
            ("res_model", "=", records._name),
            ("res_field", "=", self.name),
            ("res_id", "in", records.ids),
        ]
        data = {
            att.res_id: self._convert_attachment_to_cache(att)
            for att in records.env["ir.attachment"].sudo().search(domain)
        }
        records.env.cache.insert_missing(records, self, map(data.get, records._ids))

    def create(self, record_values):
        if not record_values:
            return
        for record, value in record_values:
            if value:
                cache_value = self.convert_to_cache(value, record)
                attachment = self._create_attachment(record, cache_value)
                cache_value = self._convert_attachment_to_cache(attachment)
                record.env.cache.update(
                    record,
                    self,
                    [cache_value],
                    dirty=False,
                )

    def _create_attachment(self, record, cache_value: FSFileValue):
        ir_attachment = (
            record.env["ir.attachment"]
            .sudo()
            .with_context(
                binary_field_real_user=record.env.user,
            )
        )
        create_value = self._prepare_attachment_create_values(record, cache_value)
        return ir_attachment.create(create_value)

    def _prepare_attachment_create_values(self, record, cache_value: FSFileValue):
        return {
            "name": cache_value.name,
            "raw": cache_value.getvalue(),
            "res_model": record._name,
            "res_field": self.name,
            "res_id": record.id,
            "type": "binary",
        }

    def write(self, records, value):
        # the code is copied from the standard Odoo Binary field
        # with the following changes:
        # - the value is not encoded in base64 and we therefore write on
        #  ir.attachment.raw instead of ir.attachment.datas

        # discard recomputation of self on records
        records.env.remove_to_compute(self, records)
        # update the cache, and discard the records that are not modified
        cache = records.env.cache
        cache_value = self.convert_to_cache(value, records)
        records = cache.get_records_different_from(records, self, cache_value)
        if not records:
            return records
        if self.store:
            # determine records that are known to be not null
            not_null = cache.get_records_different_from(records, self, None)

        if self.store:
            # Be sure to invalidate the cache for the modified records since
            # the value of the field has changed and the new value will be linked
            # to the attachment record used to store the file in the storage.
            cache.remove(records, self)
        else:
            # if the field is not stored and a value is set, we need to
            # set the value in the cache since the value (the case for computed
            # fields)
            cache.update(records, self, itertools.repeat(cache_value))
        # retrieve the attachments that store the values, and adapt them
        if self.store and any(records._ids):
            real_records = records.filtered("id")
            atts = (
                records.env["ir.attachment"]
                .sudo()
                .with_context(
                    binary_field_real_user=records.env.user,
                )
            )
            if not_null:
                atts = atts.search(
                    [
                        ("res_model", "=", self.model_name),
                        ("res_field", "=", self.name),
                        ("res_id", "in", real_records.ids),
                    ]
                )
            if value:
                filename = cache_value.name
                content = cache_value.getvalue()
                # update the existing attachments
                atts.write({"raw": content, "name": filename})
                atts_records = records.browse(atts.mapped("res_id"))
                # set new value in the cache since we have the reference to the
                # attachment record and a new access to the field will nomore
                # require to load the attachment record
                for record in atts_records:
                    new_cache_value = self._convert_attachment_to_cache(
                        atts.filtered(lambda att, rec=record: att.res_id == rec.id)
                    )
                    cache.update(record, self, [new_cache_value], dirty=False)
                # create the missing attachments
                missing = real_records - atts_records
                if missing:
                    created = atts.browse()
                    for record in missing:
                        created |= self._create_attachment(record, cache_value)
                    for att in created:
                        record = records.browse(att.res_id)
                        new_cache_value = self._convert_attachment_to_cache(att)
                        record.env.cache.update(
                            record, self, [new_cache_value], dirty=False
                        )
            else:
                atts.unlink()

        return records

    def _convert_attachment_to_cache(self, attachment: IrAttachment) -> FSFileValue:
        return FSFileValue(attachment=attachment)

    def _get_filename(self, record):
        return record.env.context.get("fs_filename", self.name)

    def convert_to_cache(self, value, record, validate=True):
        if value is None or value is False:
            return None
        if isinstance(value, FSFileValue):
            return value
        if isinstance(value, dict):
            if "content" not in value and value.get("url"):
                # we come from an onchange
                # The id is the third element of the url
                att_id = value["url"].split("/")[3]
                attachment = record.env["ir.attachment"].sudo().browse(int(att_id))
                return self._convert_attachment_to_cache(attachment)
            return FSFileValue(
                name=value["filename"], value=base64.b64decode(value["content"])
            )
        if isinstance(value, IOBase):
            name = getattr(value, "name", None)
            if name is None:
                name = self._get_filename(record)
            return FSFileValue(name=name, value=value)
        if isinstance(value, bytes):
            return FSFileValue(
                name=self._get_filename(record), value=base64.b64decode(value)
            )
        raise ValueError(
            f"Invalid value for {self}: {value}\n"
            "Should be base64 encoded bytes or a file-like object"
        )

    def convert_to_write(self, value, record):
        return self.convert_to_cache(value, record)

    def convert_to_read(self, value, record, use_name_get=True):
        if value is None or value is False:
            return None
        if isinstance(value, FSFileValue):
            res = {
                "filename": value.name,
                "size": value.size,
                "mimetype": value.mimetype,
            }
            if value.attachment:
                res["url"] = value.internal_url
            else:
                res["content"] = base64.b64encode(value.getvalue()).decode("ascii")
            return res
        raise ValueError(
            f"Invalid value for {self}: {value}\n"
            "Should be base64 encoded bytes or a file-like object"
        )
