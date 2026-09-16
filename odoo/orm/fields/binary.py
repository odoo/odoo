import base64
import binascii
import contextlib
import functools
import typing
import warnings
from collections.abc import Callable, Sequence
from operator import attrgetter
from typing import override

from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.libs.filesystem import guess_mimetype
from odoo.tools import SQL, human_size
from odoo.tools.image import image_process

from ..domain.ast import Domain, DomainCondition, OptimizationLevel
from ..primitives import COLLECTION_TYPES
from .base import Field

_debug = DebugLog(__name__)

if typing.TYPE_CHECKING:
    from odoo.tools import Query

    from .._typing import ModelLike
    from ..models import BaseModel

_BINARY = memoryview

_SVG_MAGIC_BYTES = frozenset({b"P", b"<"})


class Binary(Field[bytes | typing.Literal[False]]):
    type = "binary"
    is_binary = True
    cache_truthiness_matches = True

    prefetch = False
    _depends_context = ("bin_size",)
    attachment = True

    @property
    def is_attachment_backed(self) -> bool:
        return self.attachment

    @override
    def _optimize_condition(
        self, condition: DomainCondition, model: BaseModel, level: OptimizationLevel
    ) -> Domain:
        if level != OptimizationLevel.BASIC:
            return condition
        operator = condition.operator
        value = condition.value
        if self.attachment:
            is_existence_check = (
                operator in ("in", "not in")
                and isinstance(value, COLLECTION_TYPES)
                and set(value) == {False}
            )
            if not is_existence_check:
                raise condition._prepare_condition_error(
                    "Binary field stored in attachment, accepts only existence "
                    "check (('field', 'in', [False]) or its negation)"
                )
        if operator.endswith("like"):
            raise condition._prepare_condition_error(
                "Cannot use like operators with binary fields",
                error=NotImplementedError,
            )
        return condition

    bin_size_field: str = ""

    @functools.cached_property
    def column_type(self):
        return None if self.attachment else ("bytea", "bytea")

    @override
    def get_depends(
        self, model: BaseModel
    ) -> tuple[typing.Iterable[str], typing.Iterable[str]]:
        depends, depends_context = super().get_depends(model)
        return depends, (*depends_context, "bin_size_" + self.name)

    def _get_attrs(self, model_class, name):
        attrs = super()._get_attrs(model_class, name)
        if not attrs.get("store", True):
            attrs["attachment"] = False
            _debug.logic(
                "field.binary.attachment_disabled_unstored",
                model=model_class._name,
                field=name,
            )
        return attrs

    _description_attachment = property(attrgetter("attachment"))

    @override
    def convert_to_column(
        self,
        value: typing.Any,
        record: ModelLike,
        values: dict[str, typing.Any] | None = None,
        validate: bool = True,
    ) -> bytes | None:
        if not value:
            return None
        if isinstance(value, str):
            value = value.encode()
        if validate and value[:1] in _SVG_MAGIC_BYTES:
            try:
                decoded_value = base64.b64decode(
                    value.translate(None, delete=b"\r\n"), validate=True
                )
            except binascii.Error:
                decoded_value = value
            is_svg = guess_mimetype(decoded_value).startswith("image/svg")
            _debug.logic(
                "field.binary.svg_probe",
                model=self.model_name,
                field=self.name,
                is_svg=is_svg,
                system=record.env.is_system(),
            )
            if is_svg and not record.env.is_system():
                raise UserError(record.env._("Only admins can upload SVG files."))
        if isinstance(value, bytes):
            return value
        try:
            return str(value).encode("ascii")
        except UnicodeEncodeError as e:
            raise UserError(
                record.env._(
                    "ASCII characters are required for %(value)s in %(field)s",
                    value=value,
                    field=self.name,
                )
            ) from e

    @override
    def get_column_update(self, record: ModelLike) -> bytes | None:
        bin_size_name = "bin_size_" + self.name
        record = record.with_context(**{"bin_size": False, bin_size_name: False})
        value = self._get_cache(record.env)[record.id]
        return self.convert_to_column(value, record, validate=False)

    @override
    def convert_to_cache(
        self, value: typing.Any, record: ModelLike, validate: bool = True
    ) -> bytes | None:
        if isinstance(value, _BINARY):
            return bytes(value)
        if isinstance(value, str):
            return value.encode()
        if isinstance(value, int) and (
            record.env.context.get("bin_size")
            or record.env.context.get("bin_size_" + self.name)
        ):
            value = human_size(value)
            return value.encode() if value else None
        return None if value is False else value

    @override
    def convert_to_record(
        self, value: typing.Any, record: ModelLike
    ) -> bytes | typing.Literal[False]:
        if isinstance(value, _BINARY):
            return bytes(value)
        return False if value is None else value

    @override
    def compute_value(self, records: ModelLike, validate: bool = True) -> None:
        bin_size_name = "bin_size_" + self.name
        under_bin_size = records.env.context.get("bin_size") or records.env.context.get(
            bin_size_name
        )
        if _debug.logic.enabled and under_bin_size:
            _debug.logic(
                "field.binary.compute_under_bin_size",
                model=self.model_name,
                field=self.name,
                records=len(records),
                strategy="size_field" if self.bin_size_field else "compute_then_size",
            )
        if under_bin_size and self.bin_size_field:
            field_cache = self._get_cache(records.env)
            for record in records:
                field_cache[record.id] = self.convert_to_cache(
                    human_size(record[self.bin_size_field]), record
                )
            return
        if under_bin_size:
            records_no_bin_size = records.with_context(
                **{"bin_size": False, bin_size_name: False}
            )
            super().compute_value(records_no_bin_size, validate=validate)
            field_cache_data = self._get_cache(records_no_bin_size.env)
            field_cache_size = self._get_cache(records.env)
            for record in records:
                try:
                    value = field_cache_data[record.id]
                    if not self.is_column:
                        with contextlib.suppress(TypeError, binascii.Error):
                            value = base64.b64decode(value)
                    if isinstance(value, (bytes, _BINARY)):
                        value = human_size(len(value))
                    cache_value = self.convert_to_cache(value, record)
                    field_cache_size[record.id] = cache_value
                except KeyError:
                    pass
        else:
            super().compute_value(records, validate=validate)

    @override
    def read(self, records: BaseModel) -> None:

        def _encode(s: str | bool) -> bytes | bool:
            if isinstance(s, str):
                return s.encode("utf-8")
            return s

        assert self.attachment
        context = records.env.context
        bin_size = context.get("bin_size") or context.get("bin_size_" + self.name)
        data = records.env.registry.file_store.read_field(
            records, self.name, bin_size=bool(bin_size)
        )
        if bin_size:
            data = {res_id: _encode(size) for res_id, size in data.items()}
        _debug.perf.count(
            "field.binary.attachments_read",
            model=self.model_name,
            field=self.name,
            records=len(records),
            attachments=len(data),
            bin_size=bool(bin_size),
        )
        self._insert_cache(records, map(data.get, records._ids))

    @override
    def create(self, record_values: Sequence[tuple[BaseModel, typing.Any]]) -> None:
        assert self.attachment
        if not record_values:
            return
        env = record_values[0][0].env
        attachments = env.registry.file_store.create_field(
            env,
            self.model_name,
            self.name,
            [(record.id, value) for record, value in record_values if value],
        )
        _debug.lifecycle(
            "field.binary.attachments_created",
            model=self.model_name,
            field=self.name,
            records=len(record_values),
            attachments=len(attachments),
        )

    @override
    def mark_dirty(self, records: BaseModel, value: typing.Any) -> None:
        records = records.with_context(
            **{"bin_size": False, "bin_size_" + self.name: False}
        )
        if not self.attachment:
            super().mark_dirty(records, value)
            return

        records, cache_value = self._mark_dirty_prologue(records, value)
        if not records:
            return
        if self.store:
            not_null = self._filter_not_equal(records, None)

        self._update_cache(records, cache_value)

        if self.store and any(records._ids):
            real_records = records.filtered("id")
            file_store = records.env.registry.file_store
            atts = file_store.of_field(
                real_records if not_null else records.browse(), self.name
            )
            if value:
                if atts:
                    atts.write({"datas": value})
                atts_records = records.browse(atts.mapped("res_id"))
                missing = real_records - atts_records
                _debug.logic(
                    "field.binary.attachments_written",
                    model=self.model_name,
                    field=self.name,
                    records=len(real_records),
                    updated=len(atts),
                    created=len(missing),
                )
                if missing:
                    file_store.create_field(
                        records.env,
                        self.model_name,
                        self.name,
                        [(record.id, value) for record in missing],
                    )
            else:
                _debug.logic(
                    "field.binary.attachments_unlinked",
                    model=self.model_name,
                    field=self.name,
                    attachments=len(atts),
                )
                atts.unlink()

    @override
    def filter_function(
        self,
        records: BaseModel,
        field_expr: str,
        operator: str,
        value: typing.Any,
    ) -> Callable[[BaseModel], bool]:
        # the cache holds bytes; a domain spells the base64 as text
        if operator == "in" and isinstance(value, COLLECTION_TYPES):
            value = {v.encode() if isinstance(v, str) else v for v in value}
        return super().filter_function(records, field_expr, operator, value)

    @override
    def condition_to_sql(
        self,
        field_expr: str,
        operator: str,
        value: typing.Any,
        model: BaseModel,
        alias: str,
        query: Query,
    ) -> SQL:
        if not self.attachment or field_expr != self.name:
            return super().condition_to_sql(
                field_expr, operator, value, model, alias, query
            )
        assert operator in ("in", "not in") and set(value) == {False}, (
            "Should have been done in Domain optimization"
        )
        with_file = model.env.registry.file_store.field_set_query(model, self.name)
        return SQL(
            "%s%s IN %s",
            model._field_to_sql(alias, "id", query),
            SQL(" NOT") if operator == "in" else SQL(),
            with_file.subselect("res_id"),
        )


class Image(Binary):
    max_width = 0
    max_height = 0
    verify_resolution = True

    @override
    def setup(self, model: BaseModel) -> None:
        super().setup(model)
        if not model._abstract and not model._log_access:
            warnings.warn(
                f"Image field {self} requires the model to have _log_access = True",
                stacklevel=1,
            )

    @override
    def create(self, record_values: Sequence[tuple[BaseModel, typing.Any]]) -> None:
        new_record_values: list[tuple[BaseModel, typing.Any]] = []
        for record, value in record_values:
            new_value = self._process_image(value, record.env)
            new_record_values.append((record, new_value))
            cache_value = self.convert_to_cache(
                value if self.related else new_value, record
            )
            self._update_cache(record, cache_value)
        super().create(new_record_values)

    @override
    def mark_dirty(self, records: BaseModel, value: typing.Any) -> None:
        records = records.with_context(
            **{"bin_size": False, "bin_size_" + self.name: False}
        )
        try:
            new_value = self._process_image(value, records.env)
        except UserError as exc:
            if not any(records._ids):
                _debug.logic(
                    "field.image.invalid_on_new_ignored",
                    model=self.model_name,
                    field=self.name,
                    error=type(exc).__name__,
                )
                return
            raise

        super().mark_dirty(records, new_value)
        if self.related:
            cache_value = self.convert_to_cache(value, records)
            self._update_cache(records, cache_value, dirty=True)

    @override
    def _inverse_related(self, records: BaseModel) -> None:
        super()._inverse_related(records)
        if not (self.max_width and self.max_height):
            return
        for record in records:
            value = self._process_related(record[self.name], record.env)
            self._update_cache(record, value, dirty=True)

    def _process_image(
        self, value: typing.Any, env: typing.Any
    ) -> bytes | typing.Literal[False]:
        if self.readonly and (
            (not self.max_width and not self.max_height)
            or (
                isinstance(self.related_field, Image)
                and self.max_width == self.related_field.max_width
                and self.max_height == self.related_field.max_height
            )
        ):
            return value
        try:
            img = base64.b64decode(value or "")
        except Exception as e:
            raise UserError(env._("Image is not encoded in base64.")) from e

        if img and guess_mimetype(img, "") == "image/webp":
            if not self.max_width and not self.max_height:
                return value
            resized = env.registry.file_store.resized_webp(
                env, img, max(self.max_width, self.max_height)
            )
            return resized or value

        return (
            base64.b64encode(
                image_process(
                    img or None,
                    size=(self.max_width, self.max_height),
                    verify_resolution=self.verify_resolution,
                )
                or b""
            )
            or False
        )

    @override
    def _process_related(
        self, value: typing.Any, env: typing.Any
    ) -> bytes | typing.Literal[False]:
        try:
            return self._process_image(super()._process_related(value, env), env)
        except UserError:
            return False
