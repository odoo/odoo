import contextlib
import functools
import itertools
import logging
import math
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime
from enum import StrEnum
from typing import Any, NamedTuple

import psycopg

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.datetime import utc
from odoo.libs.debug_log import DebugLog
from odoo.libs.json import loads as json_loads
from odoo.tools import OrderedSet
from odoo.tools.misc import DATE_LENGTH
from odoo.tools.translate import LazyTranslate, code_translations

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)
_lt = LazyTranslate(__name__)

REFERENCING_FIELDS = frozenset({None, "id", ".id"})


def escape_import_message(text: str) -> str:
    return text.replace("%", "%%")


def escape_import_params(params: Any) -> Any:
    match params:
        case str():
            return escape_import_message(params)
        case dict():
            return {k: escape_import_message(str(v)) for k, v in params.items()}
        case tuple():
            return tuple(escape_import_message(str(v)) for v in params)
    return params


def parse_number(value: Any, cast: Callable[[Any], Any]) -> Any:
    if isinstance(value, str) and "_" in value:
        raise ValueError(value)
    return cast(value)


BOOLEAN_TRUE_TERMS = (_lt("yes"), _lt("true"))
BOOLEAN_FALSE_TERMS = (_lt("no"), _lt("false"))
BOOLEAN_TRANSLATIONS = (
    BOOLEAN_TRUE_TERMS[0],
    BOOLEAN_FALSE_TERMS[0],
    BOOLEAN_TRUE_TERMS[1],
    BOOLEAN_FALSE_TERMS[1],
)


class ImportPolicy(StrEnum):
    REPORT = "report"
    SKIP_RECORD = "import_skip_records"
    SET_EMPTY = "import_set_empty_fields"


class SkipRecord:
    __slots__ = ()

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "SKIP"


SKIP = SkipRecord()

_UNCONVERTED = object()


class PropertyField(NamedTuple):
    comodel_name: str | None
    name: str


type ConvertibleField = fields.Field | PropertyField
type Converter = Callable[[Any], tuple[Any, list]]
type RecordConverter = Callable[[dict, Callable], dict | None]


class RefLookup(NamedTuple):
    id: int | bool | None
    field_type: str
    error_msg: str
    warnings: list


class OdooImportWarning(Warning):
    pass


class ImportReferenceNotFound(ValueError):
    pass


class IrFieldsConverter(models.AbstractModel):
    _name = "ir.fields.converter"
    _description = "Fields Converter"

    @api.model
    def _prepare_import_error(
        self,
        error_type: type[Exception],
        error_msg: str,
        error_params: str | dict[str, Any] | tuple = (),
        error_args: dict[str, Any] | None = None,
    ) -> Exception:
        return error_type(
            error_msg % escape_import_params(error_params), error_args or {}
        )

    @api.model
    def _get_field_path(self, field: ConvertibleField) -> str:
        return "/".join(
            self.env.context.get("parent_fields_hierarchy", []) + [field.name]
        )

    @api.model
    def _get_policy_paths(self) -> tuple[Sequence[str], Sequence[str]]:
        context = self.env.context
        if not context.get("import_file"):
            return (), ()
        return (
            context.get(ImportPolicy.SKIP_RECORD) or (),
            context.get(ImportPolicy.SET_EMPTY) or (),
        )

    @api.model
    def _get_policy(self, field: ConvertibleField) -> ImportPolicy:
        path = self._get_field_path(field)
        skip_records, set_empty_fields = self._get_policy_paths()
        if path in skip_records:
            _debug.logic("import_policy", field=path, policy="skip_record")
            return ImportPolicy.SKIP_RECORD
        if path in set_empty_fields:
            _debug.logic("import_policy", field=path, policy="set_empty")
            return ImportPolicy.SET_EMPTY
        return ImportPolicy.REPORT

    @api.model
    def _get_field_path_for_error(self, field: str, value: Any) -> list[str]:
        field_path = [*(self.env.context.get("parent_fields_hierarchy") or []), field]
        while isinstance(value, list) and value:
            record = value[0]
            if (
                not isinstance(record, dict)
                or len(record) != 1
                or not record.keys() <= REFERENCING_FIELDS
            ):
                break
            subfield = next(iter(record))
            if subfield:
                field_path.append(subfield)
            value = record[subfield]
        return field_path

    @api.model
    def _prepare_unknown_field_error(self, model: models.BaseModel) -> Exception:
        return self._prepare_import_error(
            ValueError,
            self.env._("Field '%%(field)s' does not exist on model '%s'"),
            model._name,
        )

    @api.model
    def _prepare_unsupported_type_error(self, field: fields.Field) -> Exception:
        return self._prepare_import_error(
            ValueError,
            self.env._(
                "Field '%%(field)s' cannot be imported (unsupported field type '%s')"
            ),
            field.type,
        )

    @api.model
    def _prepare_import_error_from_exception(
        self, exception: Exception, fname: str, value: Any, in_import_file: Any
    ) -> Exception:
        if isinstance(exception, (UnicodeEncodeError, UnicodeDecodeError, UserError)):
            _debug.logic(
                "import_error.classified",
                field=fname,
                kind="unicode" if isinstance(exception, UnicodeError) else "user",
            )
            exception = ValueError(escape_import_message(str(exception)))
        if isinstance(exception, ValueError):
            if in_import_file:
                error_info = exception.args[1] if len(exception.args) > 1 else None
                if isinstance(error_info, dict) and not error_info.get("field_path"):
                    error_info["field_path"] = self._get_field_path_for_error(
                        fname, value
                    )
            return exception
        _logger.error(
            "Import converter for field %r failed on a %s value",
            fname,
            type(value).__name__,
            exc_info=exception,
        )
        _debug.logic(
            "import_error.classified",
            field=fname,
            kind="unexpected",
            error=type(exception).__name__,
        )
        return self._prepare_import_error(
            ValueError,
            self.env._(
                "Field '%%(field)s' could not be imported from a "
                "value of type '%s'; see the server logs for details"
            ),
            type(value).__name__,
        )

    @api.model
    def _get_converter_record(self, model: models.BaseModel) -> RecordConverter:
        model = self.env[model._name]
        model_fields = model._fields
        converter_cache: dict[str, Converter | None] = {}
        in_import_file = self.env.context.get("import_file")

        def resolve_converter(name: str, field: fields.Field) -> Converter | None:
            if name not in converter_cache:
                converter_cache[name] = self._resolve_converter_field(field)
                _debug.logic(
                    "converter_resolved",
                    model=model._name,
                    field=name,
                    type=field.type,
                    supported=converter_cache[name] is not None,
                )
            return converter_cache[name]

        def convert_one(fname: str, value: Any, log: Callable) -> Any:
            field = model_fields.get(fname)
            if field is None:
                _debug.logic("convert_skipped", field=fname, reason="unknown_field")
                log(fname, self._prepare_unknown_field_error(model))
                return _UNCONVERTED
            converter = resolve_converter(fname, field)
            if converter is None:
                _debug.logic(
                    "convert_skipped",
                    field=fname,
                    reason="unsupported",
                    type=field.type,
                )
                log(fname, self._prepare_unsupported_type_error(field))
                return _UNCONVERTED
            if not value:
                return False
            try:
                converted, warnings = converter(value)
            except psycopg.Error as e:
                if not isinstance(e, psycopg.DataError):
                    raise
                _debug.logic(
                    "convert_failed", field=fname, type=field.type, error="DataError"
                )
                log(fname, ValueError(escape_import_message(str(e))))
                return _UNCONVERTED
            except Exception as e:
                _debug.logic(
                    "convert_failed",
                    field=fname,
                    type=field.type,
                    error=type(e).__name__,
                )
                log(
                    fname,
                    self._prepare_import_error_from_exception(
                        e, fname, value, in_import_file
                    ),
                )
                return _UNCONVERTED
            if _debug.logic.enabled and warnings:
                _debug.logic("convert_warned", field=fname, warnings=len(warnings))
            for warning in warnings:
                log(fname, warning)
            return converted

        def convert_record(record: dict, log: Callable) -> dict | None:
            converted = {}
            for fname, value in record.items():
                if fname in REFERENCING_FIELDS:
                    continue
                value = convert_one(fname, value, log)
                if value is SKIP:
                    _debug.logic("record_skipped", model=model._name, field=fname)
                    return None
                if value is not _UNCONVERTED:
                    converted[fname] = value
            _debug.pipeline(
                "record_converted",
                model=model._name,
                given=len(record),
                converted=len(converted),
            )
            return converted

        return convert_record

    @api.model
    def _resolve_converter_field(self, field: fields.Field) -> Converter | None:
        converter = self._get_value_converter(field.type)
        if converter is None:
            return None
        return functools.partial(converter, field)

    @api.model
    def _get_value_converter(self, field_type: str) -> Callable | None:
        return getattr(self, f"_str_to_{field_type}", None)

    @api.model
    def _str_to_json(self, field: ConvertibleField, value: str) -> tuple[Any, list]:
        try:
            return json_loads(value), []
        except ValueError:
            _debug.logic("json_rejected", field=field.name)
            msg = self.env._(
                "'%s' does not seem to be a valid JSON for field '%%(field)s'"
            )
            raise self._prepare_import_error(ValueError, msg, value) from None

    @api.model
    def _str_to_properties(
        self, field: ConvertibleField, value: str | list
    ) -> tuple[Any, list]:
        msg = self.env._(
            "Unable to import '%%(field)s' Properties field as a whole, target individual property instead."
        )
        if isinstance(value, str):
            try:
                value = json_loads(value)
            except ValueError:
                _debug.logic("properties_rejected", field=field.name, reason="json")
                raise self._prepare_import_error(ValueError, msg) from None

        if not isinstance(value, list) or not all(
            isinstance(property_dict, dict) for property_dict in value
        ):
            _debug.logic("properties_rejected", field=field.name, reason="not_list")
            raise self._prepare_import_error(ValueError, msg, {"value": value})

        value = [dict(property_dict) for property_dict in value]
        _debug.pipeline("properties_imported", field=field.name, properties=len(value))

        warnings = []
        for property_dict in value:
            self._check_property_keys(property_dict)
            sub_field = PropertyField(
                comodel_name=property_dict.get("comodel"),
                name=f"{field.name}.{property_dict['name']}",
            )
            try:
                self._check_property_definition(property_dict)
                val = property_dict.get("value")
                if val in (None, "", [], ()):
                    continue
                coerced, ws = self._convert_property_value(
                    sub_field, val, property_dict
                )
            except ValueError as exc:
                self._add_error_subfield(exc, property_dict["string"])
                raise
            warnings.extend(ws)
            if coerced is SKIP:
                _debug.logic("properties_skip_record", field=sub_field.name)
                return SKIP, warnings
            property_dict["value"] = coerced

        return value, warnings

    _PROPERTY_CONVERTERS = {
        "selection": "_property_to_selection",
        "tags": "_property_to_tags",
        "many2one": "_property_to_relational",
        "many2many": "_property_to_relational",
    }

    _PROPERTY_TYPE_KEYS = {
        "selection": ("selection", 2),
        "tags": ("tags", 3),
        "many2one": ("comodel", 0),
        "many2many": ("comodel", 0),
    }

    @api.model
    def _convert_property_value(
        self, field: PropertyField, val: Any, property_dict: dict
    ) -> tuple[Any, list]:
        property_type = property_dict["type"]
        coerce = self._PROPERTY_CONVERTERS.get(property_type)
        if coerce is not None:
            return getattr(self, coerce)(field, val, property_dict)
        converter = self._get_value_converter(property_type)
        if converter is None:
            _debug.logic("property_uncoerced", field=field.name, type=property_type)
            return val, []
        try:
            return converter(field, val)
        except ValueError:
            skipped = self._get_policy_fallback_value(field)
            if skipped is None:
                raise
            _debug.logic("property_fallback", field=field.name, skip=skipped is SKIP)
            return skipped, []

    @api.model
    def _check_property_keys(self, property_dict: dict) -> None:
        if property_dict.keys() >= {"name", "type", "string"} and isinstance(
            property_dict["type"], str
        ):
            return
        _debug.logic("property_definition_rejected", reason="missing_keys")
        msg = self.env._(
            "'%(value)s' does not seem to be a valid Property value for field '%%(field)s'. Each property need at least 'name', 'type' and 'string' attribute."
        )
        raise self._prepare_import_error(ValueError, msg, {"value": property_dict})

    @api.model
    def _check_property_definition(self, property_dict: dict) -> None:
        required, width = self._PROPERTY_TYPE_KEYS.get(property_dict["type"], (None, 0))
        if required is None:
            return
        if required not in property_dict:
            _debug.logic(
                "property_definition_rejected",
                reason="missing_definition",
                type=property_dict["type"],
            )
            raise self._prepare_import_error(
                ValueError,
                self.env._("Property '%%(field)s' is missing its '%s' definition."),
                required,
            )
        if width and not self._is_definition_rows(property_dict[required], width):
            _debug.logic(
                "property_definition_rejected",
                reason="malformed_rows",
                type=property_dict["type"],
            )
            raise self._prepare_import_error(
                ValueError,
                self.env._("Property '%%(field)s' has a malformed '%s' definition."),
                required,
            )
        if required == "comodel" and not self._is_importable_model(
            property_dict[required]
        ):
            _debug.logic(
                "property_definition_rejected",
                reason="unknown_comodel",
                type=property_dict["type"],
            )
            raise self._prepare_import_error(
                ValueError,
                self.env._("Property '%%(field)s' targets unknown model '%s'."),
                property_dict[required],
            )

    @api.model
    def _is_importable_model(self, comodel_name: Any) -> bool:
        return isinstance(comodel_name, str) and comodel_name in self.env

    @staticmethod
    def _is_definition_rows(rows: Any, width: int) -> bool:
        return isinstance(rows, (list, tuple)) and all(
            isinstance(row, (list, tuple)) and len(row) == width for row in rows
        )

    @staticmethod
    def _match_choice(value: Any, choices: Sequence[Sequence]) -> Any:
        # a value outranks every label, exactly as the column index orders
        # its tokens, so an item's label can never shadow another item's value
        token = str(value).strip().lower()
        for position in (0, 1):
            for choice in choices:
                if value == choice[position]:
                    return choice[0]
            for choice in choices:
                if str(choice[position]).lower() == token:
                    return choice[0]
        return None

    @api.model
    def _property_to_selection(
        self, field: PropertyField, val: Any, property_dict: dict
    ) -> tuple[Any, list]:
        choices = property_dict["selection"]
        new_val = self._match_choice(val, choices)
        if new_val is not None:
            return new_val, []

        skipped = self._get_policy_fallback_value(field)
        if skipped is not None:
            return skipped, []
        _debug.logic("property_rejected", field=field.name, kind="selection")
        raise self._prepare_import_error(
            ValueError,
            self.env._("Value '%s' not found in selection field '%%(field)s'"),
            val,
            {"moreinfo": [label for _value, label in choices]},
        )

    @api.model
    def _property_to_tags(
        self, field: PropertyField, val: Any, property_dict: dict
    ) -> tuple[Any, list]:
        choices = property_dict["tags"]
        if isinstance(val, (list, tuple)):
            tags = [tag for tag in val if tag not in (None, "")]
        else:
            tags = self._split_references(str(val))
        new_val = []
        for tag in tags:
            val_tag = self._match_choice(tag, choices)
            if val_tag is None:
                skipped = self._get_policy_fallback_value(field)
                if skipped is not None:
                    return skipped, []
                _debug.logic("property_rejected", field=field.name, kind="tag")
                raise self._prepare_import_error(
                    ValueError,
                    self.env._("Tag '%s' not found in tags field '%%(field)s'"),
                    tag,
                    {"moreinfo": [label for _value, label, *_rest in choices]},
                )
            new_val.append(val_tag)
        _debug.perf.count("property_tags_matched", field=field.name, tags=len(new_val))
        return new_val, []

    @api.model
    def _property_to_relational(
        self, field: PropertyField, val: Any, property_dict: dict
    ) -> tuple[Any, list]:
        try:
            [record] = val
        except TypeError, ValueError:
            record = None
        if not isinstance(record, dict):
            _debug.logic("property_rejected", field=field.name, kind="relational")
            raise self._prepare_import_error(
                ValueError,
                self.env._(
                    "Field '%%(field)s' expects a single reference per record, got '%s'"
                ),
                val,
            )
        multi = property_dict["type"] == "many2many"
        ids, warnings = self._get_reference_ids(field, record, multi=multi)
        if any(id_ is None for id_ in ids):
            _debug.logic(
                "property_reference_unresolved",
                field=field.name,
                multi=multi,
                unresolved=sum(1 for id_ in ids if id_ is None),
            )
            if self._get_policy(field) is ImportPolicy.SKIP_RECORD:
                return SKIP, warnings
            ids = [id_ for id_ in ids if id_]
        return (ids if multi else (ids[0] if ids else False)), warnings

    @api.model
    def _get_policy_fallback_value(self, field: ConvertibleField) -> Any:
        match self._get_policy(field):
            case ImportPolicy.SKIP_RECORD:
                return SKIP
            case ImportPolicy.SET_EMPTY:
                return False
        return None

    @api.model
    def _get_transaction_cache(self) -> dict:
        return self.env.cr.cache.setdefault(self._name, {})

    @api.model
    def _get_boolean_tokens(self) -> tuple[frozenset, frozenset]:
        tnx_cache = self._get_transaction_cache()
        cache_key = ("boolean_value_sets",)
        if cache_key not in tnx_cache:
            trues = frozenset(
                word.lower()
                for word in itertools.chain(
                    ["1"],
                    *(
                        [term._source, *self._get_boolean_translations(term._source)]
                        for term in BOOLEAN_TRUE_TERMS
                    ),
                )
            )
            falses = frozenset(
                word.lower()
                for word in itertools.chain(
                    ["", "0"],
                    *(
                        [term._source, *self._get_boolean_translations(term._source)]
                        for term in BOOLEAN_FALSE_TERMS
                    ),
                )
            )
            tnx_cache[cache_key] = (trues, falses)
            _debug.perf.count(
                "boolean_tokens_built", trues=len(trues), falses=len(falses)
            )
        return tnx_cache[cache_key]

    @api.model
    def _is_falsy_token(self, value: Any) -> bool:
        _trues, falses = self._get_boolean_tokens()
        return isinstance(value, str) and value.lower() in falses

    @api.model
    def _str_to_boolean(self, field: ConvertibleField, value: str) -> tuple[Any, list]:
        trues, falses = self._get_boolean_tokens()
        value_lower = str(value).lower()
        if value_lower in trues:
            return True, []
        if value_lower in falses:
            return False, []

        if self._get_policy(field) is ImportPolicy.SKIP_RECORD:
            return SKIP, []

        _debug.logic("value_rejected", field=field.name, kind="boolean")
        raise self._prepare_import_error(
            ValueError,
            self.env._("Unknown value '%s' for boolean field '%%(field)s'"),
            value,
            {"moreinfo": self.env._("Use '1' for yes and '0' for no")},
        )

    @api.model
    def _str_to_integer(self, field: ConvertibleField, value: str) -> tuple[int, list]:
        try:
            return parse_number(value, int), []
        except ValueError, TypeError:
            _debug.logic("value_rejected", field=field.name, kind="integer")
            raise self._prepare_import_error(
                ValueError,
                self.env._(
                    "'%s' does not seem to be an integer for field '%%(field)s'"
                ),
                value,
            ) from None

    @api.model
    def _str_to_float(self, field: ConvertibleField, value: str) -> tuple[float, list]:
        try:
            result = parse_number(value, float)
            valid = math.isfinite(result)
        except ValueError, TypeError:
            valid = False
        if not valid:
            _debug.logic("value_rejected", field=field.name, kind="float")
            raise self._prepare_import_error(
                ValueError,
                self.env._("'%s' does not seem to be a number for field '%%(field)s'"),
                value,
            )
        return result, []

    _str_to_monetary = _str_to_float

    @api.model
    def _str_to_str(self, field: ConvertibleField, value: str) -> tuple[str, list]:
        if isinstance(value, str) and getattr(field, "trim", False):
            return value.strip(), []
        return value, []

    _str_to_reference = _str_to_char = _str_to_text = _str_to_binary = _str_to_html = (
        _str_to_str
    )

    @api.model
    def _str_to_date(self, field: ConvertibleField, value: str) -> tuple[str, list]:
        try:
            if isinstance(value, str) and value[DATE_LENGTH:].strip():
                fields.Datetime.from_string(value)
            parsed_value = fields.Date.from_string(value)
            return fields.Date.to_string(parsed_value), []
        except ValueError:
            _debug.logic("value_rejected", field=field.name, kind="date")
            raise self._prepare_import_error(
                ValueError,
                self.env._(
                    "'%s' does not seem to be a valid date for field '%%(field)s'"
                ),
                value,
                {"moreinfo": self.env._("Use the format '%s'", "2012-12-31")},
            ) from None

    @api.model
    def _parse_datetime(self, value: Any) -> tuple[datetime, bool]:
        if isinstance(value, str):
            with contextlib.suppress(ValueError):
                value = datetime.fromisoformat(value)
        tz_aware = getattr(value, "tzinfo", None) is not None
        parsed = fields.Datetime.from_string(value)
        if parsed is None:
            raise ValueError(f"no datetime in {value!r}")
        return parsed, tz_aware

    @api.model
    def _str_to_datetime(self, field: ConvertibleField, value: str) -> tuple[str, list]:
        try:
            parsed_value, tz_aware = self._parse_datetime(value)
        except ValueError:
            _debug.logic("value_rejected", field=field.name, kind="datetime")
            raise self._prepare_import_error(
                ValueError,
                self.env._(
                    "'%s' does not seem to be a valid datetime for field '%%(field)s'"
                ),
                value,
                {"moreinfo": self.env._("Use the format '%s'", "2012-12-31 23:59:59")},
            ) from None

        if tz_aware:
            return fields.Datetime.to_string(parsed_value), []

        tz = self.env.tz
        _debug.logic("datetime_localized", field=field.name, tz=tz)
        return fields.Datetime.to_string(
            parsed_value.replace(tzinfo=tz).astimezone(utc)
        ), []

    @api.model
    def _get_boolean_translations(self, src: str) -> list[str]:
        tnx_cache = self._get_transaction_cache()
        cache_key = ("boolean_translations", src)
        if cache_key in tnx_cache:
            return tnx_cache[cache_key]

        values = OrderedSet()
        for lang in self.env.registry.locale.installed_langs(self.env):
            translations = code_translations.get_python_translations("base", lang)
            if src in translations:
                values.add(translations[src])

        result = tnx_cache[cache_key] = list(values)
        _debug.perf.count("boolean_translations_read", translations=len(result))
        return result

    @api.model
    def _get_selection_and_labels(
        self, field: fields.Field
    ) -> tuple[list, dict | None]:
        dynamic = self._is_dynamic_selection(field)
        selection = field._description_selection(
            self.with_context(lang="en_US" if dynamic else None).env
        )
        current_lang_labels = (
            dict(field._description_selection(self.env)) if dynamic else None
        )
        _debug.perf.count(
            "selection_read",
            model=field.model_name,
            field=field.name,
            dynamic=dynamic,
            items=len(selection),
        )
        return selection, current_lang_labels

    @staticmethod
    def _is_dynamic_selection(field: fields.Field) -> bool:
        return callable(field.selection) or isinstance(field.selection, str)

    @api.model
    def _prepare_selection_index_and_labels(
        self, field: fields.Field
    ) -> tuple[dict[str, Any], dict[str, str]]:
        selection, current_lang_labels = self._get_selection_and_labels(field)
        index: dict[str, Any] = {}
        labels = dict(selection)

        def put(token: Any, item: Any) -> None:
            if token is not None and token != "":
                index.setdefault(str(token).lower(), item)

        for item, _label in selection:
            put(item, item)
        for item, label in selection:
            put(label, item)
        if current_lang_labels is not None:
            for item, label in selection:
                translated = current_lang_labels.get(item, label)
                put(translated, item)
                labels[item] = translated
            _debug.logic("selection_index_dynamic", field=field.name, tokens=len(index))
            return index, labels

        lang = self.env.lang or "en_US"
        if "ir.model.fields.selection" not in self.env.registry:
            _debug.logic("selection_index_untranslated", field=field.name, lang=lang)
            # no translated labels without the table: the keys and the
            # declared labels answer (the DB-free tier)
            return index, labels
        selections = (
            self.env["ir.model.fields.selection"]
            .sudo()
            .search_fetch(
                [
                    ("field_id.model", "=", field.model_name),
                    ("field_id.name", "=", field.name),
                ],
                ["value"],
                order="sequence, id",
            )
        )
        names = selections._fields["name"]._get_stored_translations_multi(selections)
        for selection in selections:
            value = selection.value
            if value not in labels:
                continue
            for term_lang, txt in (names.get(selection.id) or {}).items():
                if txt is None:
                    continue
                if term_lang != "en_US":
                    put(txt, value)
                if term_lang == lang:
                    labels[value] = txt
        _debug.perf.count(
            "selection_index_built",
            model=field.model_name,
            field=field.name,
            lang=lang,
            tokens=len(index),
        )
        return index, labels

    @api.model
    def _get_selection_index(self, field: fields.Field) -> dict[str, Any]:
        return self._get_selection_index_and_labels(field)[0]

    @api.model
    def _get_selection_index_and_labels(
        self, field: fields.Field
    ) -> tuple[dict[str, Any], dict[str, str]]:
        tnx_cache = self._get_transaction_cache()
        cache_key = ("selection_index", field.model_name, field.name, self.env.lang)
        if cache_key not in tnx_cache:
            tnx_cache[cache_key] = self._prepare_selection_index_and_labels(field)
        return tnx_cache[cache_key]

    @api.model
    def _str_to_selection(self, field: fields.Field, value: str) -> tuple[Any, list]:
        index, labels = self._get_selection_index_and_labels(field)
        item = index.get(str(value).lower())
        if item is not None:
            return item, []

        skipped = self._get_policy_fallback_value(field)
        if skipped is not None:
            _debug.logic(
                "selection_value_fallback", field=field.name, skip=skipped is SKIP
            )
            return skipped, []
        _debug.logic(
            "selection_value_unknown",
            model=field.model_name,
            field=field.name,
            value=value,
        )
        raise self._prepare_import_error(
            ValueError,
            self.env._("Value '%s' not found in selection field '%%(field)s'"),
            value,
            {
                "moreinfo": [
                    labels.get(item) or str(item)
                    for item in labels
                    if labels.get(item) or item
                ]
            },
        )

    @api.model
    def _prepare_action_possible_values(
        self, field: ConvertibleField, subfield: str | None
    ) -> dict:
        action = {
            "name": "Possible Values",
            "type": "ir.actions.act_window",
            "target": "new",
            "view_mode": "list,form",
            "views": [(False, "list"), (False, "form")],
            "context": {"create": False},
            "help": self.env._("See all possible values"),
        }
        if subfield == "id":
            action["res_model"] = "ir.model.data"
            action["domain"] = [("model", "=", field.comodel_name)]
        else:
            action["res_model"] = field.comodel_name
        return action

    @api.model
    def _get_cache_and_key(
        self, field: ConvertibleField, subfield: str | None, value: Any
    ) -> tuple[Any, tuple | None]:
        cache = self.env.context.get("import_cache")
        if cache is None or not isinstance(value, str):
            return None, None
        return cache, (field.comodel_name, subfield, value)

    @api.model
    def _get_db_id(
        self,
        field: ConvertibleField,
        subfield: str | None,
        value: str,
    ) -> tuple[Any, list]:
        cache, cache_key = self._get_cache_and_key(field, subfield, value)
        if cache is not None:
            if (cached := cache.get(cache_key)) is not None:
                if subfield is None and self._flush_import(
                    model=field.comodel_name, name=value
                ):
                    _debug.logic("ref_cache_stale", field=field.name, reason="pending")
                    del cache[cache_key]
                else:
                    cached_id, cached_warnings = cached
                    _debug.perf.count(
                        "ref_cache_hit", field=field.name, subfield=subfield
                    )
                    return cached_id, list(cached_warnings)

        if subfield == ".id":
            lookup = self._get_ref_from_dbid(field, value)
        elif subfield == "id":
            lookup = self._get_ref_from_xmlid(field, value)
        elif subfield is None:
            lookup = self._get_ref_from_name(field, value)
        else:
            _debug.logic("ref_subfield_unknown", field=field.name, subfield=subfield)
            raise self._prepare_import_error(
                ValueError,
                self.env._("Unknown sub-field “%s”"),
                subfield,
            )

        if cache is not None and lookup.id:
            cache[cache_key] = (lookup.id, list(lookup.warnings))
        _debug.logic(
            "ref_lookup",
            field=field.name,
            subfield=subfield,
            found=lookup.id is not None,
            cached=cache is not None,
        )

        if lookup.id is None and self._get_policy(field) is ImportPolicy.REPORT:
            _debug.logic(
                "ref_not_found",
                field=field.name,
                subfield=subfield,
                created_failed=bool(lookup.error_msg),
            )
            raise self._prepare_ref_not_found_error(
                field, subfield, lookup.field_type, value, lookup.error_msg
            )
        return lookup.id, lookup.warnings

    @api.model
    def _flush_import(self, **selector: Any) -> bool:
        flush = self.env.context.get("import_flush")
        return flush is not None and bool(flush(**selector))

    @api.model
    def _get_ref_from_dbid(self, field: ConvertibleField, value: str) -> RefLookup:
        field_type = self.env._("database id")
        if self._is_falsy_token(value):
            return RefLookup(False, field_type, "", [])
        try:
            tentative_id = int(value)
        except ValueError:
            _debug.logic("ref_dbid_invalid", field=field.name)
            raise self._prepare_import_error(
                ValueError,
                self.env._("Invalid database id '%s' for the field '%%(field)s'"),
                value,
                {"moreinfo": self._prepare_action_possible_values(field, ".id")},
            ) from None
        exists = self.env[field.comodel_name].browse(tentative_id).exists()
        _debug.logic(
            "ref_dbid_checked",
            model=field.comodel_name,
            id=tentative_id,
            exists=bool(exists),
        )
        return RefLookup((tentative_id if exists else None), field_type, "", [])

    @api.model
    def _get_ref_from_xmlid(self, field: ConvertibleField, value: str) -> RefLookup:
        field_type = self.env._("external id")
        if self._is_falsy_token(value):
            return RefLookup(False, field_type, "", [])
        value = str(value)
        if "." in value:
            xmlid = value
        else:
            xmlid = f"{self.env.context.get('_import_current_module', '')}.{value}"
        self._flush_import(xml_id=xmlid)
        id = self._xmlid_to_record_id(xmlid, self.env[field.comodel_name])
        _debug.logic(
            "ref_xmlid_resolved",
            model=field.comodel_name,
            qualified="." in value,
            found=id is not None,
        )
        return RefLookup(id, field_type, "", [])

    @api.model
    def _get_ref_from_name(self, field: ConvertibleField, value: str) -> RefLookup:
        field_type = self.env._("name")
        warnings = []
        if value == "":
            return RefLookup(False, field_type, "", warnings)
        RelatedModel = self.env[field.comodel_name]
        ids = RelatedModel.name_search(name=value, operator="=")
        flushed = False
        if not ids:
            # a miss may be a record an earlier row of this import is still
            # holding; flushing before every search split a 3000-row import
            # into 3000 single-row creates
            self._flush_import(model=field.comodel_name)
            flushed = True
            ids = RelatedModel.name_search(name=value, operator="=")
        elif self._flush_import(model=field.comodel_name, name=value):
            # a hit with a namesake pending in the batch: the pending one is
            # a match too, and the caller must see both
            flushed = True
            ids = RelatedModel.name_search(name=value, operator="=")
        _debug.perf.count(
            "ref_name_searched",
            model=RelatedModel._name,
            matches=len(ids),
            flushed=flushed,
        )
        if ids:
            if len(ids) > 1:
                warnings.append(self._prepare_multiple_matches_warning(value, len(ids)))
            id, _name = ids[0]
            return RefLookup(id, field_type, "", warnings)

        name_create_enabled_fields = (
            self.env.context.get("name_create_enabled_fields") or {}
        )
        if RelatedModel._name_create_on_import or name_create_enabled_fields.get(
            self._get_field_path(field)
        ):
            _debug.logic(
                "ref_name_create_allowed",
                model=RelatedModel._name,
                by_model=RelatedModel._name_create_on_import,
            )
            try:
                with self.env.cr.savepoint():
                    id, _name = RelatedModel.name_create(name=value)
                _debug.lifecycle("ref_name_created", model=RelatedModel._name, id=id)
                return RefLookup(id, field_type, "", warnings)
            except (UserError, ValueError, psycopg.Error) as exc:
                _debug.logic(
                    "ref_name_create_failed",
                    model=RelatedModel._name,
                    error=type(exc).__name__,
                )
                error_msg = self.env._(
                    "Cannot create new '%s' records from their name alone. Please create those records manually and try importing again.",
                    RelatedModel._description,
                )
                return RefLookup(None, field_type, error_msg, warnings)
        _debug.logic(
            "ref_name_unresolved",
            model=RelatedModel._name,
            name_create_allowed=False,
        )
        return RefLookup(None, field_type, "", warnings)

    @api.model
    def _prepare_multiple_matches_warning(self, value: Any, count: int) -> Warning:
        return OdooImportWarning(
            self.env._(
                'Found multiple matches for value "%(value)s" in field "%%(field)s" (%(match_count)s matches)',
                value=escape_import_message(str(value)),
                match_count=count,
            )
        )

    NAME_SEARCH_LIMIT = 100

    @api.model
    def _is_name_prefetchable(self, comodel: models.BaseModel) -> bool:
        # the batch below re-derives what name_search(name, operator="=")
        # matches, which is only the default _search_display_name's contract
        cls = type(comodel)
        return (
            cls.name_search is models.BaseModel.name_search
            and cls._search_display_name is models.BaseModel._search_display_name
        )

    @api.model
    def _prefetch_name_references(
        self, model: models.BaseModel, records: Sequence[dict]
    ) -> None:
        cache = self.env.context.get("import_cache")
        if cache is None:
            return
        wanted: dict[tuple[str, str | None], OrderedSet] = defaultdict(OrderedSet)
        for record in records:
            for fname, value in record.items():
                field = model._fields.get(fname)
                if field is None or not (field.is_many2one or field.is_many2many):
                    continue
                if not isinstance(value, list):
                    continue
                for sub in value:
                    if not (isinstance(sub, dict) and len(sub) == 1):
                        continue
                    [(subfield, raw)] = sub.items()
                    if subfield not in REFERENCING_FIELDS or not isinstance(raw, str):
                        continue
                    if field.is_many2many:
                        references = self._split_references(raw)
                    else:
                        references = [raw.strip()]
                    wanted[field.comodel_name, subfield].update(
                        reference
                        for reference in references
                        if reference
                        and not self._is_falsy_token(reference)
                        and (field.comodel_name, subfield, reference) not in cache
                    )
        for (comodel_name, subfield), references in wanted.items():
            if len(references) < 2:
                continue
            if subfield is None:
                self._prefetch_names_of(comodel_name, references, cache)
            elif subfield == ".id":
                self._prefetch_dbids_of(comodel_name, references, cache)
            else:
                self._prefetch_xmlids_of(comodel_name, references, cache)

    @api.model
    def _prefetch_dbids_of(
        self, comodel_name: str, references: OrderedSet, cache: Any
    ) -> None:
        by_id: dict[int, list[str]] = defaultdict(list)
        for reference in references:
            with contextlib.suppress(ValueError):
                by_id[int(reference)].append(reference)
        if not by_id:
            return
        alive = set(self.env[comodel_name].browse(list(by_id)).exists()._ids)
        for id_, spellings in by_id.items():
            if id_ in alive:
                for reference in spellings:
                    cache[(comodel_name, ".id", reference)] = (id_, [])
        _debug.perf.count(
            "ref_dbid_prefetched",
            model=comodel_name,
            wanted=len(references),
            alive=len(alive),
        )

    @api.model
    def _prefetch_xmlids_of(
        self, comodel_name: str, references: OrderedSet, cache: Any
    ) -> None:
        if "ir.model.data" not in self.env.registry:
            return
        module = self.env.context.get("_import_current_module", "")
        by_xmlid: dict[str, list[str]] = defaultdict(list)
        for reference in references:
            xmlid = reference if "." in reference else f"{module}.{reference}"
            by_xmlid[xmlid].append(reference)
        comodel = self.env[comodel_name]
        rows = self.env.registry.xmlids.resolve(self.env, list(by_xmlid), comodel)
        found = 0
        for _id, module, name, res_model, _res_id, _noupdate, alive_id in rows:
            if res_model != comodel_name or not alive_id:
                continue
            found += 1
            for reference in by_xmlid[f"{module}.{name}"]:
                cache[(comodel_name, "id", reference)] = (alive_id, [])
        _debug.perf.count(
            "ref_xmlid_prefetched",
            model=comodel_name,
            wanted=len(references),
            found=found,
        )

    @api.model
    def _prefetch_names_of(
        self, comodel_name: str, names: OrderedSet, cache: Any
    ) -> None:
        comodel = self.env[comodel_name]
        if not self._is_name_prefetchable(comodel):
            _debug.logic(
                "ref_name_prefetch_skipped", model=comodel_name, reason="override"
            )
            return
        fnames = [
            fname
            for fname in comodel._get_rec_names_search_fields()
            if not comodel._is_rec_names_search_cyclic(fname)
        ]
        if not fnames:
            return
        to_fetch = list(dict.fromkeys(fname.split(".", 1)[0] for fname in fnames))
        try:
            found = comodel.search_fetch(
                Domain("display_name", "in", list(names)), to_fetch
            )
            matches: dict[str, list[int]] = defaultdict(list)
            for record in found:
                for fname in fnames:
                    value = record.mapped(fname) if "." in fname else record[fname]
                    if isinstance(value, models.BaseModel):
                        tokens = value.mapped("display_name")
                    elif isinstance(value, list):
                        tokens = [*value, *map(str, value)]
                    else:
                        tokens = [value, str(value)]
                    for token in tokens:
                        if isinstance(token, str) and token in names:
                            if record.id not in matches[token]:
                                matches[token].append(record.id)
                            break
        except UserError, psycopg.Error:
            _debug.logic(
                "ref_name_prefetch_skipped", model=comodel_name, reason="error"
            )
            return
        for name, ids in matches.items():
            ids = ids[: self.NAME_SEARCH_LIMIT]
            warnings = []
            if len(ids) > 1:
                warnings.append(self._prepare_multiple_matches_warning(name, len(ids)))
            cache[(comodel_name, None, name)] = (ids[0], warnings)
        _debug.perf.count(
            "ref_name_prefetched",
            model=comodel_name,
            wanted=len(names),
            found=len(matches),
            records=len(found),
        )

    @api.model
    def _prepare_ref_not_found_error(
        self,
        field: ConvertibleField,
        subfield: str | None,
        field_type: str,
        value: Any,
        error_msg: str,
    ) -> Exception:
        if error_msg:
            message = self.env._(
                "No matching record found for %(field_type)s '%(value)s' in field '%%(field)s' and the following error was encountered when we attempted to create one: %(error_message)s"
            )
        else:
            message = self.env._(
                "No matching record found for %(field_type)s '%(value)s' in field '%%(field)s'"
            )
        display_value = value[:50] if isinstance(value, str) else value
        error_info_dict = {
            "moreinfo": self._prepare_action_possible_values(field, subfield)
        }
        if self.env.context.get("import_file"):
            error_info_dict.update({"value": display_value, "field_type": field_type})
            if error_msg:
                error_info_dict["error_message"] = error_msg
        return self._prepare_import_error(
            ImportReferenceNotFound,
            message,
            {
                "field_type": field_type,
                "value": display_value,
                "error_message": error_msg,
            },
            error_info_dict,
        )

    @api.model
    def _xmlid_to_record_id(self, xmlid: str, model: models.BaseModel) -> int | None:
        res_model, res_id = self.env.registry.xmlids.target(
            self.env, xmlid, raise_if_not_found=False
        )
        if not res_id:
            _debug.logic("xmlid_unresolved", model=model._name, reason="no_data")
            return None
        self._check_xmlid_model(xmlid, res_model, model)
        if not model.browse(res_id).exists():
            _debug.logic("xmlid_unresolved", model=model._name, reason="record_gone")
            return None
        return res_id

    @api.model
    def _check_xmlid_model(
        self, xmlid: str, found_model: str, model: models.BaseModel
    ) -> None:
        if found_model == model._name:
            return
        _debug.logic("xmlid_model_mismatch", found=found_model, expected=model._name)
        raise self._prepare_import_error(
            ValueError,
            self.env._(
                "External id '%(xmlid)s' refers to a '%(found_model)s' "
                "record, but field '%%(field)s' expects a "
                "'%(expected_model)s' record"
            ),
            {
                "xmlid": xmlid,
                "found_model": found_model,
                "expected_model": model._name,
            },
        )

    @api.model
    def _get_subfield_referencing(self, record: dict) -> str | None:
        fieldset = set(record)
        if fieldset - REFERENCING_FIELDS:
            _debug.logic("reference_rejected", reason="indirect_create")
            raise self._prepare_import_error(
                ValueError,
                self.env._(
                    "Can not create Many-To-One records indirectly, import the field separately"
                ),
            )
        if not fieldset:
            _debug.logic("reference_rejected", reason="missing")
            raise self._prepare_import_error(
                ValueError,
                self.env._(
                    "Missing a reference (name, external id or database id) for field '%%(field)s'"
                ),
            )
        if len(fieldset) > 1:
            _debug.logic("reference_rejected", reason="ambiguous", given=len(fieldset))
            raise self._prepare_import_error(
                ValueError,
                self.env._(
                    "Ambiguous specification for field '%%(field)s', only provide one of name, external id or database id"
                ),
            )

        [subfield] = fieldset
        return subfield

    @api.model
    def _split_references(self, raw: str) -> list[str]:
        if not isinstance(raw, str):
            _debug.logic("references_rejected", type=type(raw).__name__)
            raise self._prepare_import_error(
                ValueError,
                self.env._(
                    "Field '%%(field)s' expects its references as comma-separated "
                    "text, got a value of type '%s'"
                ),
                type(raw).__name__,
            )
        return [
            stripped for reference in raw.split(",") if (stripped := reference.strip())
        ]

    @api.model
    def _strip_reference(self, raw: Any) -> Any:
        return raw.strip() if isinstance(raw, str) else raw

    @api.model
    def _get_record_single(self, values: Any) -> dict:
        if not isinstance(values, list) or len(values) != 1:
            raise self._prepare_import_error(
                ValueError,
                self.env._(
                    "Field '%%(field)s' expects a single reference per record, got '%s'"
                ),
                values,
            )
        record = values[0]
        if not isinstance(record, dict):
            raise self._prepare_import_error(
                ValueError,
                self.env._("Field '%%(field)s' expects a reference record, got '%s'"),
                record,
            )
        return record

    @api.model
    def _get_records_nested(self, values: Any) -> list[dict]:
        if not isinstance(values, list) or not all(
            isinstance(record, dict) for record in values
        ):
            raise self._prepare_import_error(
                ValueError,
                self.env._(
                    "Field '%%(field)s' expects a list of sub-records, got '%s'"
                ),
                values,
            )
        return values

    @api.model
    def _get_reference_ids(
        self, field: ConvertibleField, record: dict, *, multi: bool
    ) -> tuple[list[int | None], list]:
        subfield = self._get_subfield_referencing(record)
        raw = record[subfield]
        references = (
            self._split_references(raw) if multi else [self._strip_reference(raw)]
        )
        ids = []
        warnings = []
        for reference in references:
            id_, ws = self._get_db_id(field, subfield, reference)
            ids.append(id_)
            warnings.extend(ws)
        _debug.pipeline(
            "references_resolved",
            field=field.name,
            subfield=subfield,
            references=len(references),
            unresolved=sum(1 for id_ in ids if id_ is None),
        )
        return ids, warnings

    @api.model
    def _str_to_many2one(
        self, field: ConvertibleField, values: list[dict]
    ) -> tuple[Any, list]:
        record = self._get_record_single(values)
        ids, warnings = self._get_reference_ids(field, record, multi=False)
        id_ = ids[0]
        if id_ is None:
            fallback = self._get_policy_fallback_value(field)
            _debug.logic("many2one_fallback", field=field.name, skip=fallback is SKIP)
            return (False if fallback is None else fallback), warnings
        return id_, warnings

    _str_to_many2one_reference = _str_to_integer

    @api.model
    def _str_to_many2many(
        self, field: ConvertibleField, value: list[dict]
    ) -> tuple[Any, list]:
        if isinstance(value, list) and any(
            isinstance(record, dict) and set(record) - REFERENCING_FIELDS
            for record in value
        ):
            return self._str_to_many2many_subrecords(field, value)
        record = self._get_record_single(value)
        ids, warnings = self._get_reference_ids(field, record, multi=True)

        if any(id is None for id in ids) and (
            self._get_policy(field) is ImportPolicy.SKIP_RECORD
        ):
            _debug.logic("many2many_skip_record", field=field.name)
            return SKIP, warnings

        ids = [id for id in ids if id]
        _debug.logic("many2many_converted", field=field.name, ids=len(ids))
        return [Command.set(ids)], warnings

    @api.model
    def _str_to_many2many_subrecords(
        self, field: ConvertibleField, value: list[dict]
    ) -> tuple[Any, list]:
        commands, warnings = self._subrecords_to_commands(
            field, self._get_records_nested(value)
        )
        if commands is SKIP:
            return SKIP, warnings
        _debug.logic(
            "many2many_subrecords_converted", field=field.name, commands=len(commands)
        )
        return [Command.clear(), *commands], warnings

    @api.model
    def _add_error_subfield(self, exception: Exception, label: str) -> None:
        if not exception.args or not isinstance(exception.args[0], str):
            return
        label = escape_import_message(str(label))
        arg0 = exception.args[0].replace("%(field)s", f"%(field)s/{label}")
        exception.args = (arg0, *exception.args[1:])

    @api.model
    def _get_converter_nested(
        self, field: ConvertibleField, hierarchy: list[str]
    ) -> RecordConverter:
        cache = self.env.context.get("import_cache")
        converters = None
        if cache is not None:
            # one always-hot entry of the reference LRU, so a wide import
            # cannot evict a nested converter behind its own references
            converters = cache.get("nested_converters")
            if converters is None:
                converters = cache["nested_converters"] = {}
        key = (tuple(hierarchy), field.comodel_name)
        if converters is not None and (cached := converters.get(key)) is not None:
            return cached

        _debug.perf.count(
            "nested_converter_built",
            field=field.name,
            comodel=field.comodel_name,
            depth=len(hierarchy),
        )
        convert = self.with_context(
            parent_fields_hierarchy=list(hierarchy)
        )._get_converter_record(self.env[field.comodel_name])
        if converters is not None:
            converters[key] = convert
        return convert

    @api.model
    def _str_to_one2many(
        self, field: ConvertibleField, records: list[dict]
    ) -> tuple[Any, list]:
        records = self._get_records_nested(records)
        if len(records) == 1 and set(records[0]) <= REFERENCING_FIELDS:
            record = records[0]
            subfield = self._get_subfield_referencing(record)
            records = [
                {subfield: item} for item in self._split_references(record[subfield])
            ]
            _debug.logic(
                "one2many_references_split",
                field=field.name,
                subfield=subfield,
                records=len(records),
            )
        commands, warnings = self._subrecords_to_commands(field, records)
        if commands is SKIP:
            return SKIP, warnings
        _debug.pipeline(
            "one2many_converted",
            field=field.name,
            commands=len(commands),
            warnings=len(warnings),
        )
        return commands, warnings

    @api.model
    def _subrecords_to_commands(
        self, field: ConvertibleField, records: list[dict]
    ) -> tuple[Any, list]:
        commands: list = []
        warnings: list = []
        parent_fields_hierarchy = self.env.context.get(
            "parent_fields_hierarchy", []
        ) + [field.name]

        comodel_fields = self.env[field.comodel_name]._fields

        def log(f: str, exception: Exception | Warning) -> None:
            if isinstance(exception, Warning):
                warnings.append(exception)
                return
            subfield = comodel_fields.get(f)
            self._add_error_subfield(exception, subfield.string if subfield else f)
            error_info = exception.args[1] if len(exception.args) > 1 else None
            if isinstance(error_info, dict) and not error_info.get("field_path"):
                error_info["field_path"] = [*parent_fields_hierarchy, f]
            raise exception

        convert = self._get_converter_nested(field, parent_fields_hierarchy)

        linked = 0
        created = 0  # debuglog
        for record in records:
            id = None
            refs = {k: v for k, v in record.items() if k in REFERENCING_FIELDS}
            writable = convert(record, log)
            if writable is None:
                _debug.logic("subrecords_skip_record", field=field.name)
                return SKIP, warnings
            if refs:
                subfield = self._get_subfield_referencing(refs)
                try:
                    id, w2 = self._get_db_id(field, subfield, record[subfield])
                    warnings.extend(w2)
                except ImportReferenceNotFound:
                    if subfield != "id":
                        raise
                    _debug.logic("subrecord_xmlid_deferred", field=field.name)
                    writable["id"] = record["id"]
                if id is None and self._get_policy(field) is ImportPolicy.SKIP_RECORD:
                    _debug.logic("subrecords_skip_record", field=field.name)
                    return SKIP, warnings

            if id:
                linked += 1
                commands.append(Command.link(id))
                if writable:
                    commands.append(Command.update(id, writable))
            elif writable or not refs:
                created += 1  # debuglog
                commands.append(Command.create(writable))
        _debug.pipeline(
            "subrecords_to_commands",
            field=field.name,
            records=len(records),
            linked=linked,
            created=created,
            blank=len(records) - linked - created,
            commands=len(commands),
        )
        return commands, warnings
