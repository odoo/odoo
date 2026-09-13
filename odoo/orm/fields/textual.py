import typing
from difflib import unified_diff
from operator import attrgetter
from typing import override

from markupsafe import Markup

from odoo.exceptions import AccessError, UserError
from odoo.libs.colors import DEFAULT, GREEN, RED, colorize
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import (
    pattern_to_translated_trigram_pattern,
    pg_varchar,
    value_to_translated_trigram_pattern,
)
from odoo.tools import SQL, OrderedSet, html_normalize, html_sanitize
from odoo.tools.misc import SENTINEL, Sentinel
from odoo.tools.translate import html_translate

from ..domain.ast import Domain, DomainCondition, OptimizationLevel
from ..primitives import COLLECTION_TYPES, SQL_OPERATORS
from . import _field_ddl as _ddl
from . import _field_translation as _translation
from ._field_translation import LangProxyDict
from .base import Field, _logger, _prepare_fast_get

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterable, MutableMapping

    from odoo.tools import Query

    from .._typing import IdType, ModelClass, ModelLike, ModelType
    from ..models import BaseModel
    from ..runtime import Environment
    from ._field_stubs import TranslateDialect

_debug = DebugLog(__name__)


def _get_string_comparand(value: typing.Any) -> typing.Any:
    if value is None or isinstance(value, (str, bool, bytes, bytearray, SQL)):
        return value
    return str(value)


def _string_from_cache(
    field: BaseString, value: typing.Any, record: BaseModel
) -> typing.Any:
    if callable(field.translate):
        return field._get_uncached(record, record.env, record._ids[0])
    return False if value is None else value


def _markup_from_cache(
    field: BaseString, value: typing.Any, record: BaseModel
) -> typing.Any:
    if callable(field.translate):
        return field._get_uncached(record, record.env, record._ids[0])
    return field.convert_to_record(value, record)


class BaseString(Field[str | typing.Literal[False]]):
    translate: bool | TranslateDialect = False
    size = None
    is_text = True

    @override
    def _optimize_condition(
        self, condition: DomainCondition, model: BaseModel, level: OptimizationLevel
    ) -> Domain:
        operator = condition.operator
        if (
            level != OptimizationLevel.BASIC
            or operator not in ("in", "not in", ">", "<", ">=", "<=")
            or "." in condition.field_expr
        ):
            return condition

        value = condition.value
        if isinstance(value, COLLECTION_TYPES):
            coerced = [_get_string_comparand(v) for v in value]
            if coerced == list(value):
                return condition
            _debug.logic(
                "field.string.comparands_coerced",
                model=model._name,
                field=condition.field_expr,
                operator=operator,
                values=len(coerced),
            )
            return DomainCondition(condition.field_expr, operator, OrderedSet(coerced))
        coerced = _get_string_comparand(value)
        if coerced is value:
            return condition
        _debug.logic(
            "field.string.comparand_coerced",
            model=model._name,
            field=condition.field_expr,
            operator=operator,
            type=type(value).__name__,
        )
        return DomainCondition(condition.field_expr, operator, coerced)

    falsy_value = ""

    def __init__(self, string: str | Sentinel = SENTINEL, **kwargs: typing.Any) -> None:
        if "translate" in kwargs and not callable(kwargs["translate"]):
            kwargs["translate"] = bool(kwargs["translate"])
        super().__init__(string=string, **kwargs)

    if typing.TYPE_CHECKING:

        @typing.overload
        def __get__(self, record: None, owner: typing.Any = None) -> typing.Self: ...
        @typing.overload
        def __get__(
            self, record: BaseModel, owner: typing.Any = None
        ) -> str | typing.Literal[False]: ...
        @typing.overload
        def __get__(self, record: object, owner: typing.Any = None) -> typing.Any: ...

        @override
        def __get__(
            self, record: typing.Any, owner: typing.Any = None
        ) -> typing.Any: ...

    else:
        __get__ = _prepare_fast_get(_string_from_cache)

    @override
    def _get_cache_miss(
        self, record: BaseModel, env: Environment, record_id: IdType
    ) -> typing.Any:
        if _translation.is_fallback_required(self, record_id):
            fb_val = _translation.get_scalar_fallback(self, env, record_id)
            if fb_val is not SENTINEL:
                return self.convert_to_record(fb_val, record)
        return super()._get_cache_miss(record, env, record_id)

    def _get_lang_cache_key(self, env: Environment, lang: str) -> tuple:
        return _translation.get_lang_cache_key(self, env, lang)

    def _get_lang_fallback_cache_key(self, env: Environment) -> tuple:
        return _translation.get_fallback_cache_key(self, env)

    _related_translate = property(attrgetter("translate"))

    def _description_translate(self, env: Environment) -> bool:
        return bool(self.translate)

    @override
    def setup_related(self, model: BaseModel) -> None:
        super().setup_related(model)
        if self.store and self.translate:
            _debug.logic(
                "field.translate.stored_related",
                model=self.model_name,
                field=self.name,
                related=self.related,
            )
            _logger.warning(
                "Translated stored related field (%s) will not be computed correctly in all languages",
                self,
            )

    def get_depends(self, model: BaseModel) -> tuple[Iterable[str], Iterable[str]]:
        if self.translate is True:
            dep, dep_ctx = super().get_depends(model)
            extra = tuple(dict.fromkeys(ctx for ctx in dep_ctx if ctx != "lang"))
            if extra and self.store:
                _debug.logic(
                    "field.translate.context_depends_ignored",
                    model=self.model_name,
                    field=self.name,
                    ignored=list(extra),
                )
                _logger.warning(
                    "Translated stored fields (%s) cannot depend on context: "
                    "the flushed column keeps one value per language; "
                    "ignoring context dependencies %s",
                    self,
                    extra,
                )
                return dep, ("lang",)
            return dep, ("lang", *extra)
        if callable(self.translate) and self.store:
            dep, dep_ctx = super().get_depends(model)
            if dep_ctx:
                _debug.logic(
                    "field.translate.context_depends_ignored",
                    model=self.model_name,
                    field=self.name,
                    ignored=list(dep_ctx),
                )
                _logger.warning(
                    "Translated stored fields (%s) cannot depend on context",
                    self,
                )
            return dep, ()
        return super().get_depends(model)

    def _convert_db_column(
        self, model: ModelLike, column: dict[str, typing.Any]
    ) -> None:
        _ddl.convert_db_column_translatable(self, model, column)

    def get_trans_terms(self, value: str | None) -> list[str]:
        return _translation.get_trans_terms(self, value)

    def get_text_content(self, term: str) -> str:
        return _translation.get_text_content(self, term)

    @override
    def convert_to_column(
        self,
        value: typing.Any,
        record: ModelLike,
        values: dict | None = None,
        validate: bool = True,
    ) -> str | None:
        return self.convert_to_cache(value, record, validate)

    @override
    def convert_to_cache(
        self, value: typing.Any, record: ModelLike, validate: bool = True
    ) -> str | None:
        if value is None or value is False:
            return None
        if (
            value.__class__ is str
            and self.size is None
            and not (validate and callable(self.translate))
        ):
            return value
        if isinstance(value, bytes):
            s = value.decode()
        else:
            s = str(value)
        if self.size is not None:
            s = s[: self.size]
        if validate and callable(self.translate):
            return self.translate(lambda t: None, s)
        return s

    @override
    def _compute_related(self, records: BaseModel) -> None:
        if records.env.context.get("edit_translations"):
            records = records.with_context(
                edit_translations=None, check_translations=True
            )
        super()._compute_related(records)

    @override
    def convert_to_record(
        self, value: typing.Any, record: ModelLike
    ) -> str | typing.Literal[False]:
        if value is None:
            return False
        if not callable(self.translate):
            return value
        if isinstance(value, dict):
            lang = self.get_translation_lang(record.env)
            value = value[lang]
        field_ = self
        record_: typing.Any = record
        while not field_.store and field_.related and field_.related_field is not None:
            path = ".".join(field_._related_names[:-1])
            record_ = record_.mapped(path)[:1] if path else record_
            field_ = field_.related_field
        if field_ is not self:
            return field_.convert_to_record(value, record_)
        if record.env.context.get("edit_translations") and self.get_trans_terms(value):
            _debug.logic(
                "field.translate.edit_translations_value",
                model=self.model_name,
                field=self.name,
                record=record.id,
            )
            return _translation.edit_translations_value(self, value, record)
        return value

    @override
    def convert_to_write(self, value: typing.Any, record: ModelLike) -> typing.Any:
        return value

    def get_translation_dictionary(
        self,
        from_lang_value: str,
        to_lang_values: dict[str, str],
    ) -> dict[str, dict[str, str]]:
        return _translation.get_translation_dictionary(
            self, from_lang_value, to_lang_values
        )

    def _get_stored_translations(self, record: ModelLike) -> dict[str, str] | None:
        return _translation.get_stored_translations(self, record)

    def _get_stored_translations_multi(
        self, records: ModelLike
    ) -> dict[IdType, dict[str, str] | None]:
        return _translation.get_stored_translations_multi(self, records, ())

    def get_translation_lang(self, env: Environment) -> str:
        return _translation.get_translation_lang(self, env)

    def get_translation_fallback_langs(self, env: Environment) -> tuple[str, ...]:
        return _translation.get_fallback_langs(self, env)

    def _get_cache_impl(self, env: Environment) -> MutableMapping[IdType, typing.Any]:
        if self.translate is True:
            return super()._get_cache_impl(env)
        cache = super()._get_cache_impl(env)
        if not self.translate or env.context.get("prefetch_langs"):
            return cache
        lang = self.get_translation_lang(env)
        return LangProxyDict(self, cache, lang)

    def _iter_cache_missing_ids(self, records: ModelLike) -> typing.Iterator[IdType]:
        if callable(self.translate) and records.env.context.get("prefetch_langs"):
            records = records.with_context(prefetch_langs=False)
        return super()._iter_cache_missing_ids(records)

    def _to_prefetch(self, record: ModelType) -> ModelType:
        if callable(self.translate) and record.env.context.get("prefetch_langs"):
            return (
                super()
                ._to_prefetch(record.with_context(prefetch_langs=False))
                .with_env(record.env)
            )
        return super()._to_prefetch(record)

    def _insert_cache(self, records: ModelLike, values: Iterable[typing.Any]) -> None:
        if not self.translate:
            super()._insert_cache(records, values)
            return
        _translation.insert_cache(self, records, values)

    def _update_cache(
        self, records: ModelLike, cache_value: typing.Any, dirty: bool = False
    ) -> None:
        if (
            self.translate
            and cache_value is not None
            and _translation.update_cache(self, records, cache_value, dirty)
        ):
            return
        super()._update_cache(records, cache_value, dirty)

    @override
    def mark_dirty(self, records: BaseModel, value: typing.Any) -> None:
        if not self.translate or value is False or value is None:
            if self.translate is True and (value is False or value is None):
                _debug.logic(
                    "field.translate.cleared_all_langs",
                    model=self.model_name,
                    field=self.name,
                    records=len(records),
                )
                self._invalidate_cache(records.env, records._ids)
            super().mark_dirty(records, value)
            return
        _translation.mark_dirty(self, records, value)

    def _mark_dirty_model_term_translation(
        self, records: BaseModel, cache_value: typing.Any, lang: str
    ) -> None:
        _translation.mark_dirty_model_term_translation(self, records, cache_value, lang)

    def _reconcile_obsolete_terms(
        self,
        get_translation_dictionary: dict,
        new_terms: set,
        lang: str,
        env: Environment,
    ) -> None:
        _translation.reconcile_obsolete_terms(
            self, get_translation_dictionary, new_terms, lang, env
        )

    @override
    def to_sql(self, model: ModelLike, alias: str) -> SQL:
        sql_field = super().to_sql(model, alias)
        if self.translate and not model.env.context.get("prefetch_langs"):
            langs = self.get_translation_fallback_langs(model.env)
            _debug.logic(
                "field.translate.to_sql",
                model=model._name,
                field=self.name,
                langs=list(langs),
            )
            sql_field_langs = [SQL("%s->>%s", sql_field, lang) for lang in langs]
            if len(sql_field_langs) == 1:
                return sql_field_langs[0]
            return SQL("COALESCE(%s)", SQL(", ").join(sql_field_langs))
        return sql_field

    def get_expression_getter(
        self, field_expr: str
    ) -> Callable[[BaseModel], typing.Any]:
        if field_expr != "display_name.no_error":
            return super().get_expression_getter(field_expr)

        get_display_name = super().get_expression_getter("display_name")

        def getter(record):
            try:
                return get_display_name(record)
            except AccessError:
                return ""

        return getter

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
        if self.translate and model.env.context.get("prefetch_langs"):
            model = model.with_context(prefetch_langs=False)
        base_condition = super().condition_to_sql(
            field_expr, operator, value, model, alias, query
        )

        if (
            self.translate
            and value
            and operator in ("in", "like", "ilike", "=like", "=ilike")
            and self.index == "trigram"
            and model.pool.has_trigram
            and (
                isinstance(value, str)
                or (
                    isinstance(value, COLLECTION_TYPES)
                    and all(isinstance(v, str) for v in value)
                )
            )
        ):
            if operator == "in" and len(value) == 1:
                value = value_to_translated_trigram_pattern(next(iter(value)))
            elif operator != "in":
                assert isinstance(value, str)
                value = pattern_to_translated_trigram_pattern(value)
            else:
                value = "%"

            _debug.logic(
                "field.translate.trigram_condition",
                model=model._name,
                field=self.name,
                operator=operator,
                applied=value != "%",
            )
            if value == "%":
                return base_condition

            raw_sql_field = self.to_sql(model.with_context(prefetch_langs=True), alias)
            sql_left = SQL("jsonb_path_query_array(%s, '$.*')::text", raw_sql_field)
            sql_operator = SQL_OPERATORS["like" if operator == "in" else operator]
            sql_right = SQL("%s", self.convert_to_column(value, model, validate=False))
            unaccent = model.env.registry.unaccent
            return SQL(
                "(%s%s%s AND %s)",
                unaccent(sql_left),
                sql_operator,
                unaccent(sql_right),
                base_condition,
            )
        return base_condition


class Char(BaseString):
    type = "char"
    cache_is_record_value = True
    cache_truthiness_matches = True
    cache_is_orderable = True
    cache_is_read_value = True
    trim: bool = True

    def _setup_attrs__(self, model_class: ModelClass, name: str) -> None:
        super()._setup_attrs__(model_class, name)
        assert self.size is None or isinstance(self.size, int), (
            f"Char field {self} with non-integer size {self.size!r}"
        )

    @property
    def _column_type(self) -> tuple[str, str]:  # type: ignore[override]
        return ("varchar", pg_varchar(self.size))

    @override
    def update_db_column(self, model: ModelLike, column: dict[str, typing.Any]) -> None:
        _ddl.widen_varchar_column(self, model, column)
        super().update_db_column(model, column)

    _related_size = property(attrgetter("size"))
    _related_trim = property(attrgetter("trim"))
    _description_size = property(attrgetter("size"))
    _description_trim = property(attrgetter("trim"))

    def get_depends(self, model: BaseModel) -> tuple[Iterable[str], Iterable[str]]:
        depends, depends_context = super().get_depends(model)

        if (
            self.name == "display_name"
            and self.compute
            and not self.store
            and model._rec_name
            and model._fields[model._rec_name].base_field.translate
            and "lang" not in depends_context
        ):
            depends_context = [*depends_context, "lang"]
            _debug.logic(
                "field.char.display_name_depends_on_lang",
                model=model._name,
                rec_name=model._rec_name,
            )

        return depends, depends_context


class Text(BaseString):
    type = "text"
    cache_is_record_value = True
    cache_truthiness_matches = True
    cache_is_orderable = True
    cache_is_read_value = True
    _column_type = ("text", "text")


class Html(BaseString):
    type = "html"
    is_html = True
    cache_truthiness_matches = True
    _column_type = ("text", "text")

    if not typing.TYPE_CHECKING:
        __get__ = _prepare_fast_get(_markup_from_cache)

    sanitize: bool = True
    sanitize_overridable: bool = False
    sanitize_tags: bool = True
    sanitize_attributes: bool = True
    sanitize_style: bool = False
    sanitize_form: bool = True
    sanitize_conditional_comments: bool = True
    sanitize_output_method: str = "html"
    strip_style: bool = False
    strip_classes: bool = False

    @override
    def _get_attrs(self, model_class: ModelClass, name: str) -> dict[str, typing.Any]:
        attrs = super()._get_attrs(model_class, name)
        if attrs.get("sanitize") == "email_outgoing":
            _debug.logic(
                "field.html.sanitize_email_outgoing",
                model=model_class._name,
                field=name,
            )
            attrs["sanitize"] = True
            attrs.update(
                {
                    key: value
                    for key, value in {
                        "sanitize_tags": False,
                        "sanitize_attributes": False,
                        "sanitize_conditional_comments": False,
                        "sanitize_output_method": "xml",
                    }.items()
                    if key not in attrs
                }
            )
        elif attrs.get("translate") is True and attrs.get("sanitize", True):
            attrs["translate"] = html_translate
            _debug.logic(
                "field.html.translate_by_terms",
                model=model_class._name,
                field=name,
            )
        return attrs

    _related_sanitize = property(attrgetter("sanitize"))
    _related_sanitize_tags = property(attrgetter("sanitize_tags"))
    _related_sanitize_attributes = property(attrgetter("sanitize_attributes"))
    _related_sanitize_style = property(attrgetter("sanitize_style"))
    _related_strip_style = property(attrgetter("strip_style"))
    _related_strip_classes = property(attrgetter("strip_classes"))

    _description_sanitize = property(attrgetter("sanitize"))
    _description_sanitize_tags = property(attrgetter("sanitize_tags"))
    _description_sanitize_attributes = property(attrgetter("sanitize_attributes"))
    _description_sanitize_style = property(attrgetter("sanitize_style"))
    _description_strip_style = property(attrgetter("strip_style"))
    _description_strip_classes = property(attrgetter("strip_classes"))

    @override
    def convert_to_column(
        self,
        value: typing.Any,
        record: ModelLike,
        values: dict | None = None,
        validate: bool = True,
    ) -> str | None:
        value = self._convert(value, record, validate=validate)
        return super().convert_to_column(value, record, values, validate=False)

    @override
    def convert_to_cache(
        self, value: typing.Any, record: ModelLike, validate: bool = True
    ) -> str | None:
        return self._convert(value, record, validate)

    def _convert(
        self, value: typing.Any, record: ModelLike, validate: bool
    ) -> str | None:
        if value is None or value is False:
            return None

        if not validate or not self.sanitize:
            return value

        sanitize_vals: dict[str, typing.Any] = {
            "silent": True,
            "sanitize_tags": self.sanitize_tags,
            "sanitize_attributes": self.sanitize_attributes,
            "sanitize_style": self.sanitize_style,
            "sanitize_form": self.sanitize_form,
            "sanitize_conditional_comments": self.sanitize_conditional_comments,
            "output_method": self.sanitize_output_method,
            "strip_style": self.strip_style,
            "strip_classes": self.strip_classes,
        }

        if self.sanitize_overridable:
            if record.env.user.has_group("base.group_sanitize_override"):
                _debug.logic(
                    "field.html.sanitize_overridden",
                    model=self.model_name,
                    field=self.name,
                    uid=record.env.uid,
                )
                return value

            for rec in record:
                self._check_overridable_content(rec, sanitize_vals)

        with _debug.perf(
            "field.html.sanitize",
            model=self.model_name,
            field=self.name,
            length=len(value),
        ) as span:
            sanitized = html_sanitize(value, **sanitize_vals)
            span.set(sanitized_length=len(sanitized))
        return sanitized

    def _check_overridable_content(
        self, record: ModelLike, sanitize_vals: dict[str, typing.Any]
    ) -> None:
        original_value = record[self.name]
        if original_value:
            original_value_sanitized = html_sanitize(original_value, **sanitize_vals)
            original_value_normalized = html_normalize(original_value)

            if (
                not original_value_sanitized
                or original_value_normalized != original_value_sanitized
            ):
                diff = unified_diff(
                    original_value_sanitized.splitlines(),
                    original_value_normalized.splitlines(),
                )

                from odoo.logutils import root_handler_uses_colors

                with_colors = root_handler_uses_colors()
                diff_str = f"The field ({record._description}, {self.string}) will not be editable:\n"
                for line in list(diff)[2:]:
                    if with_colors:
                        color = {"-": RED, "+": GREEN}.get(line[:1], DEFAULT)
                        diff_str += colorize(line.rstrip() + "\n", color)
                    else:
                        diff_str += line.rstrip() + "\n"
                _logger.info(diff_str)
                _debug.logic(
                    "field.html.overridable_content_locked",
                    model=self.model_name,
                    field=self.name,
                    record=record.id,
                    uid=record.env.uid,
                )

                raise UserError(
                    record.env._(
                        "The field value you're saving (%(model)s %(field)s) includes content that is "
                        "restricted for security reasons. It is possible that someone "
                        "with higher privileges previously modified it, and you are therefore "
                        "not able to modify it yourself while preserving the content.",
                        model=record._description,
                        field=self.string,
                    )
                )

    @override
    def convert_to_record(
        self, value: typing.Any, record: ModelLike
    ) -> Markup | typing.Literal["", False]:
        r = super().convert_to_record(value, record)
        if isinstance(r, bytes):
            r = r.decode()
        return r and Markup(r)

    @override
    def convert_to_read(
        self,
        value: typing.Any,
        record: ModelLike,
        use_display_name: bool = True,
    ) -> Markup | typing.Literal["", False]:
        r = super().convert_to_read(value, record, use_display_name)
        if isinstance(r, bytes):
            r = r.decode()
        return r and Markup(r)

    @override
    def get_trans_terms(self, value: str | None) -> list[str]:
        return list(map(str, super().get_trans_terms(value)))
