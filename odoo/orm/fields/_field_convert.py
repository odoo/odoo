import typing
from datetime import date, datetime

from psycopg.types.json import Json as PsycopgJson

from odoo.libs.debug_log import DebugLog
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import PENDING, SENTINEL

if typing.TYPE_CHECKING:
    from .._typing import BaseModel, IdType, ModelLike
    from .base import Field

    M = typing.TypeVar("M", bound=BaseModel)


from . import _field_ddl as _ddl
from ._field_stubs import _FieldStubs

_debug = DebugLog(__name__)


class _FieldConvertMixin[T](_FieldStubs):
    def convert_to_column(
        self,
        value: typing.Any,
        record: ModelLike,
        values: dict[str, typing.Any] | None = None,
        validate: bool = True,
    ) -> typing.Any:
        if value is None or value is False:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, bytes):
            return value.decode()
        if isinstance(value, (int, float)):
            return str(value)
        raise TypeError(f"Invalid column value for {self}: {value!r}")

    @staticmethod
    def _to_json_value(value: typing.Any) -> typing.Any:
        if isinstance(value, datetime):
            return value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if isinstance(value, date):
            return value.strftime(DEFAULT_SERVER_DATE_FORMAT)
        return value

    def convert_to_column_insert(
        self,
        value: typing.Any,
        record: ModelLike,
        values: dict[str, typing.Any] | None = None,
        validate: bool = True,
    ) -> typing.Any:
        value = self.convert_to_column(value, record, values, validate)
        if self.translate:
            if value is None:
                return None
            return PsycopgJson({"en_US": value, record.env.lang or "en_US": value})
        if not self.company_dependent:
            return value
        fallback = self._get_company_dependent_fallback_raw(record)
        if value == self.convert_to_column(fallback, record):
            _debug.logic(
                "field.company_dependent.insert_as_fallback",
                model=self.model_name,
                field=self.name,
                company=record.env.company.id,
            )
            return None
        return PsycopgJson({record.env.company.id: self._to_json_value(value)})

    def _get_column_update_model_translation(
        self, record: ModelLike, record_id: IdType
    ) -> typing.Any:
        langs_dict = {}
        found = False
        for cache_key, sub_cache in record.env.core.iter_context_caches(
            typing.cast("Field", self)
        ):
            if (value := sub_cache.get(record_id, SENTINEL)) is not SENTINEL:
                found = True
                if value is not None:
                    langs_dict[cache_key[0]] = value
        if not langs_dict:
            flat_value = self._get_flat_column_value(record, record_id)
            if flat_value is SENTINEL:
                if not found:
                    raise KeyError(record_id)
            elif flat_value is not None:
                langs_dict[record.env.lang or "en_US"] = flat_value
        return PsycopgJson(langs_dict) if langs_dict else None

    def _get_flat_column_value(
        self, record: ModelLike, record_id: IdType
    ) -> typing.Any:
        flat = record.env.core.get_field_data_or_none(typing.cast("Field", self))
        return SENTINEL if flat is None else flat.get(record_id, SENTINEL)

    def _get_column_update_plain(
        self, record: ModelLike, record_id: IdType
    ) -> typing.Any:
        env = record.env
        if not self._is_context_dependent(env):
            value = env.core.get_field_data(typing.cast("Field", self))[record_id]
            if value is PENDING:
                return PENDING
            return self.convert_to_column(value, record, validate=False)
        found = False
        for _key, cache in env.core.iter_context_caches(typing.cast("Field", self)):
            if (value := cache.get(record_id, SENTINEL)) is not SENTINEL:
                found = True
                if value is not PENDING:
                    return self.convert_to_column(value, record, validate=False)
        if found:
            return PENDING
        raise KeyError(record_id)

    def _get_column_update_company_dependent(
        self, record: ModelLike, record_id: IdType
    ) -> typing.Any:
        values = {}
        found = False
        saw_pending = False
        company_index = record.env.registry.field_depends_context[self].index("company")
        for ctx_key, cache in record.env.core.iter_context_caches(
            typing.cast("Field", self)
        ):
            if (value := cache.get(record_id, SENTINEL)) is not SENTINEL:
                found = True
                if value is PENDING:
                    saw_pending = True
                else:
                    values[ctx_key[company_index]] = self._to_json_value(
                        self.convert_to_column(value, record)
                    )
        if not values:
            flat_value = self._get_flat_column_value(record, record_id)
            if flat_value is SENTINEL:
                if not found:
                    raise KeyError(record_id)
            elif flat_value is not None:
                values[record.env.company.id] = self._to_json_value(
                    self.convert_to_column(flat_value, record)
                )
        if not values and saw_pending:
            return PENDING
        return PsycopgJson(values) if values else None

    def get_column_update(self, record: ModelLike) -> typing.Any:
        record_id = record.id
        if self.translate is True:
            return self._get_column_update_model_translation(record, record_id)
        if self.translate:
            value = record.env.core.get_field_data(typing.cast("Field", self))[
                record_id
            ]
            return PsycopgJson(value) if value else None
        if not self.company_dependent:
            return self._get_column_update_plain(record, record_id)
        return self._get_column_update_company_dependent(record, record_id)

    def convert_to_cache(
        self, value: typing.Any, record: ModelLike, validate: bool = True
    ) -> typing.Any:
        return value

    def convert_to_record(self, value: typing.Any, record: ModelLike) -> T:
        return typing.cast("T", False if value is None else value)

    def convert_to_read(
        self, value: typing.Any, record: ModelLike, use_display_name: bool = True
    ) -> typing.Any:
        return False if value is None else value

    def convert_to_write(self, value: typing.Any, record: ModelLike) -> typing.Any:
        cache_value = self.convert_to_cache(value, record, validate=False)
        record_value = self.convert_to_record(cache_value, record)
        return self.convert_to_read(record_value, record)

    def convert_to_export(self, value: typing.Any, record: ModelLike) -> typing.Any:
        if not value:
            return ""
        return value

    def convert_to_display_name(
        self, value: typing.Any, record: ModelLike
    ) -> str | typing.Literal[False]:
        return str(value) if value else False

    @property
    def column_order(self) -> int:
        column_type = self.column_type
        return 0 if column_type is None else _ddl.get_column_order(column_type[0])
