import ast
import contextlib
import json
import typing
import uuid
from collections import abc, defaultdict
from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from datetime import date, datetime
from operator import attrgetter
from typing import override

from psycopg.types.json import Json as PsycopgJson

from odoo.exceptions import AccessError, MissingError, UserError
from odoo.libs.debug_log import DebugLog
from odoo.libs.json import fast_clone
from odoo.tools import SQL, OrderedSet, html_sanitize, is_list_of
from odoo.tools.misc import frozendict, has_list_types

from .._recordset import is_recordset
from ..domain import Domain
from ..domain.ast import DomainCondition, OptimizationLevel
from ..parsing import parse_field_expr
from ..primitives import COLLECTION_TYPES, SQL_OPERATORS
from ..validation import regex_alphanumeric
from ._field_sql import PYTHON_INEQUALITY_OPERATOR
from .base import Field, _logger
from .reference import REFERENCE_VERIFIED_CACHE_KEY
from .temporal import _value_to_date, _value_to_datetime

_debug = DebugLog(__name__)

if typing.TYPE_CHECKING:
    from odoo.tools import Query

    from .._typing import ModelClass, ModelLike
    from ..models import BaseModel

NoneType = type(None)


def check_property_field_value_name(property_name: str) -> None:
    if not (0 < len(property_name) <= 512) or not regex_alphanumeric.fullmatch(
        property_name
    ):
        raise ValueError(f"Wrong property field value name {property_name!r}.")


def _optimize_property_temporal_comparand(
    condition: DomainCondition, model: BaseModel
) -> Domain:
    operator = condition.operator
    if (
        operator not in ("in", "not in", ">", "<", ">=", "<=")
        or condition.field_expr.count(".") != 1
        or not isinstance(condition.value, (str, AbstractSet))
    ):
        return condition
    definition = model.get_property_definition(condition.field_expr)
    property_type = definition.get("type")

    if property_type == "date":
        value = _value_to_date(condition.value, model.env)
    elif property_type == "datetime":
        value, _ = _value_to_datetime(condition.value, model.env)
    else:
        return condition
    if isinstance(value, COLLECTION_TYPES):
        value = OrderedSet(
            str(item) if isinstance(item, (date, datetime)) else item for item in value
        )
    elif isinstance(value, (date, datetime)):
        value = str(value)

    _debug.logic(
        "field.properties.temporal_comparand",
        model=model._name,
        field_expr=condition.field_expr,
        operator=operator,
        property_type=property_type,
    )
    return DomainCondition(condition.field_expr, operator, value)


RELATIONAL_PROPERTY_TYPES = frozenset(("many2one", "many2many"))


def _is_unset(value: typing.Any) -> bool:
    return value is False or value is None or (type(value) is list and not value)


def _same_value(domain_value: typing.Any, value: typing.Any) -> bool:
    # 0 == False and 1 == True in Python; a stored 0 is not an unset property
    return domain_value == value and isinstance(domain_value, bool) is isinstance(
        value, bool
    )


def _unset_property_sql(raw_sql_field: SQL, property_name: str) -> tuple[SQL, SQL]:
    return (
        SQL("%s IS NULL", raw_sql_field),
        SQL("NOT (%s ? %s)", raw_sql_field, property_name),
    )


class Properties(Field):
    type = "properties"
    cache_truthiness_matches = False
    is_properties = True
    _column_type = ("jsonb", "jsonb")
    copy = False
    prefetch = False
    write_sequence = 10

    store = True
    readonly = False
    precompute = True

    definition: str | None = None
    definition_record: str | None = None
    definition_record_field: str | None = None

    _description_definition_record = property(attrgetter("definition_record"))

    @override
    def _optimize_condition(
        self, condition: DomainCondition, model: BaseModel, level: OptimizationLevel
    ) -> Domain:
        if level != OptimizationLevel.DYNAMIC_VALUES:
            return condition
        return _optimize_property_temporal_comparand(condition, model)

    _description_definition_record_field = property(
        attrgetter("definition_record_field")
    )

    HTML_SANITIZE_OPTIONS: typing.ClassVar[dict[str, typing.Any]] = {
        "sanitize_attributes": True,
        "sanitize_tags": True,
        "sanitize_style": False,
        "sanitize_form": True,
        "sanitize_conditional_comments": True,
        "strip_style": False,
        "strip_classes": False,
    }

    ALLOWED_TYPES = (
        "boolean",
        "integer",
        "float",
        "text",
        "char",
        "html",
        "date",
        "datetime",
        "monetary",
        "many2one",
        "many2many",
        "selection",
        "tags",
        "separator",
    )

    @override
    def _setup_attrs__(self, model_class: ModelClass, name: str) -> None:
        super()._setup_attrs__(model_class, name)
        self._setup_definition_attrs(model_class)

    def _get_definition_record(self) -> str:
        if self.definition_record is None:
            raise TypeError(f"{self} declares no definition record to read from")
        return self.definition_record

    def _get_definition_record_field(self) -> str:
        if self.definition_record_field is None:
            raise TypeError(f"{self} declares no definition record field")
        return self.definition_record_field

    def _setup_definition_attrs(self, model_class: ModelClass | BaseModel) -> None:
        if self.definition:
            assert self.definition.count(".") == 1
            self.definition_record, self.definition_record_field = (
                self.definition.rsplit(".", 1)
            )

            if not self.inherited_field:
                self._depends = (self.definition_record,)
                self.compute = self._compute
            _debug.lifecycle(
                "field.properties.definition_bound",
                model=self.model_name,
                field=self.name,
                definition_record=self.definition_record,
                definition_field=self.definition_record_field,
                computed=not self.inherited_field,
            )

    @override
    def setup_related(self, model: BaseModel) -> None:
        super().setup_related(model)
        if self.inherited_field and not self.definition:
            self.definition = self.inherited_field.definition
            _debug.logic(
                "field.properties.definition_inherited",
                model=self.model_name,
                field=self.name,
                definition=self.definition,
            )
            self._setup_definition_attrs(model)

    @override
    def convert_to_column(
        self,
        value: typing.Any,
        record: ModelLike,
        values: dict[str, typing.Any] | None = None,
        validate: bool = True,
    ) -> typing.Any:
        if not value:
            return None

        value = self.convert_to_cache(value, record, validate=validate)
        return PsycopgJson(value)

    @override
    def convert_to_cache(
        self, value: typing.Any, record: ModelLike, validate: bool = True
    ) -> dict[str, typing.Any] | None:
        if not value:
            return None

        if isinstance(value, Property):
            value = value._values

        elif isinstance(value, dict):
            value = fast_clone(self._replace_recordsets_with_ids(value, record))

        elif isinstance(value, str):
            value = json.loads(value)
            if not isinstance(value, dict):
                raise ValueError(f"Wrong property value {value!r}")

        elif isinstance(value, list):
            self._remove_display_name(value)
            value = self._list_to_dict(value)

        else:
            raise TypeError(f"Wrong property type {type(value)!r}")

        if validate:
            for property_name, property_value in value.items():
                if property_name.endswith("_html"):
                    value[property_name] = html_sanitize(
                        property_value,
                        **self.HTML_SANITIZE_OPTIONS,
                    )

        return value

    def _replace_recordsets_with_ids(
        self, values: dict[str, typing.Any], record: ModelLike
    ) -> dict[str, typing.Any]:
        if not any(is_recordset(value) for value in values.values()):
            return values

        types_by_name: dict[str, str | None] = {}
        with contextlib.suppress(AccessError, MissingError, ValueError):
            for definition in self._get_properties_definition(record) or ():
                if definition.get("name"):
                    types_by_name[definition["name"]] = definition.get("type")

        converted = dict(values)
        replaced = 0  # debuglog
        for name, value in values.items():
            if not is_recordset(value):
                continue
            property_type = types_by_name.get(name)
            if property_type == "many2one":
                converted[name] = value.id
            elif property_type == "many2many":
                converted[name] = value.ids
            else:
                raise ValueError(
                    f"Cannot store a recordset in property {name!r} of "
                    f"{self}: its definition declares "
                    f"{property_type or 'no relational type'}"
                )
            replaced += 1  # debuglog
        _debug.logic(
            "field.properties.recordsets_replaced",
            model=self.model_name,
            field=self.name,
            replaced=replaced,
            definitions=len(types_by_name),
        )
        return converted

    @override
    def convert_to_record(self, value: typing.Any, record: ModelLike) -> Property:
        return Property(value or {}, self, record)

    @override
    def convert_to_read(
        self, value: typing.Any, record: ModelLike, use_display_name: bool = True
    ) -> typing.Any:
        return self.convert_to_read_multi([value], record, use_display_name)[0]

    def convert_to_read_multi(
        self,
        values: list[typing.Any],
        records: ModelLike,
        use_display_name: bool = True,
    ) -> list[typing.Any]:
        if not records:
            return [[] for _ in values]
        if len(values) != len(records):
            raise ValueError(
                f"convert_to_read_multi: expected {len(records)} values, got {len(values)}"
            )

        result = []
        for record, value in zip(records, values, strict=True):
            value = value._values if isinstance(value, Property) else value
            if definition := self._get_properties_definition(record):
                value = value or {}
                assert isinstance(value, dict), f"Wrong type {value!r}"
                result.append(self._dict_to_list(value, definition))
            else:
                result.append([])

        res_ids_per_model = self._get_res_ids_per_model(records.env, result, records)

        for value in result:
            self._parse_json_types(value, records.env, res_ids_per_model)

        if use_display_name:
            for value in result:
                self._add_display_name(value, records.env)

        _debug.pipeline(
            "field.properties.read",
            model=self.model_name,
            field=self.name,
            records=len(records),
            with_definition=sum(1 for value in result if value),
            comodels=len(res_ids_per_model),
            display_names=use_display_name,
        )
        return result

    @override
    def convert_to_write(self, value: typing.Any, record: ModelLike) -> typing.Any:
        return value

    @override
    def convert_to_export(self, value: typing.Any, record: ModelLike) -> typing.Any:
        if isinstance(value, Property):
            value = value._values
        return value or ""

    def _get_res_ids_per_model(
        self,
        env: typing.Any,
        values_list: list[typing.Any],
        records: ModelLike | None = None,
    ) -> dict[str, set[int]]:
        ids_per_model: defaultdict[str, OrderedSet] = defaultdict(OrderedSet)
        relational: dict[str, str] = {}

        for record_values in values_list:
            for property_definition in record_values:
                comodel = property_definition.get("comodel")
                type_ = property_definition.get("type")
                property_value = property_definition.get("value") or []
                default = property_definition.get("default") or []

                if type_ not in RELATIONAL_PROPERTY_TYPES or comodel not in env:
                    continue
                relational[property_definition["name"]] = comodel

                if type_ == "many2one":
                    default = [default] if default else []
                    property_value = (
                        [property_value] if isinstance(property_value, int) else []
                    )
                elif not is_list_of(property_value, int):
                    property_value = []

                ids_per_model[comodel].update(default)
                ids_per_model[comodel].update(property_value)

        if not ids_per_model:
            return {}
        # the pairs a cursor has already seen exist stay verified until an
        # unlink discards their model (the unlink mixin does, by cache key)
        verified = env.cr.cache.setdefault(REFERENCE_VERIFIED_CACHE_KEY, {}).setdefault(
            (self.model_name, self.name), set()
        )
        unverified = any(
            (model, id_) not in verified
            for model, ids in ids_per_model.items()
            for id_ in ids
        )
        # one record asked and a statement is due: its prefetch siblings'
        # cached values name the records the next reads will ask about, so
        # they are verified in the same statement instead of one per record
        if unverified and records is not None and len(records) == 1:
            cached = self._get_cache(env)
            for sibling_id in records._prefetch_ids:
                raw = cached.get(sibling_id)
                if not isinstance(raw, dict):
                    continue
                for name, comodel in relational.items():
                    value = raw.get(name)
                    if value.__class__ is int:
                        ids_per_model[comodel].add(value)
                    elif isinstance(value, list):
                        ids_per_model[comodel].update(
                            v for v in value if v.__class__ is int
                        )

        res_ids_per_model = {}
        for model, ids in ids_per_model.items():
            unknown = [id_ for id_ in ids if (model, id_) not in verified]
            existing = env[model].browse(unknown).exists() if unknown else None
            if existing is not None:
                verified.update((model, id_) for id_ in existing._ids)
            res_ids = {id_ for id_ in ids if (model, id_) in verified}
            res_ids_per_model[model] = res_ids
            _debug.perf.count(
                "field.properties.res_ids_verified",
                field=self.name,
                comodel=model,
                requested=len(ids),
                queried=len(unknown),
                existing=len(res_ids),
            )

            for record in env[model].browse(sorted(res_ids)):
                with contextlib.suppress(AccessError):
                    record.display_name  # noqa: B018  the read IS the access check suppress() catches

        return res_ids_per_model

    @override
    def create(self, record_values: Sequence[tuple[BaseModel, typing.Any]]) -> None:
        # the row and the cache already carry the value: only a definition change
        # still has work to do after the insert
        definition_writes = [
            (record, value)
            for record, value in record_values
            if isinstance(value, list)
            and any(
                isinstance(definition, dict)
                and (
                    definition.get("definition_changed")
                    or definition.get("definition_deleted")
                )
                for definition in value
            )
        ]
        _debug.logic(
            "field.properties.create",
            model=self.model_name,
            field=self.name,
            records=len(record_values),
            definition_writes=len(definition_writes),
        )
        super().create(definition_writes)

    @override
    def mark_dirty(self, records: BaseModel, value: typing.Any) -> None:
        if isinstance(value, str):
            value = json.loads(value)

        if isinstance(value, Property):
            value = value._values

        if len(records[self._get_definition_record()]) > 1 and value:
            raise UserError(
                records.env._(
                    "Updating records with different property fields definitions is not supported. Update by separate definition instead."
                )
            )

        if isinstance(value, dict):
            return super().mark_dirty(records, value)

        definition_changed = any(
            definition.get("definition_changed") or definition.get("definition_deleted")
            for definition in (value or [])
        )
        _debug.logic(
            "field.properties.write",
            model=self.model_name,
            field=self.name,
            records=len(records),
            properties=len(value or ()),
            definition_changed=definition_changed,
        )
        if definition_changed:
            value = [
                definition
                for definition in value
                if not definition.get("definition_deleted")
            ]
            for definition in value:
                definition.pop("definition_changed", None)

            container = records[self._get_definition_record()]
            if container:
                properties_definition = fast_clone(value)
                for property_definition in properties_definition:
                    property_definition.pop("value", None)
                container[self._get_definition_record_field()] = properties_definition
                _debug.lifecycle(
                    "field.properties.definition_written",
                    model=self.model_name,
                    field=self.name,
                    container=container._name,
                    container_id=container.id,
                    properties=len(properties_definition),
                )

                _logger.info(
                    "Properties field: User #%i changed definition of %r",
                    records.env.user.id,
                    container,
                )

        return super().mark_dirty(records, value)

    def _compute(self, records: BaseModel) -> None:
        _debug.pipeline(
            "field.properties.compute",
            model=self.model_name,
            field=self.name,
            records=len(records),
        )
        for record in records.sudo():
            record[self.name] = self._add_default_values(
                record.env,
                {
                    self.name: record[self.name],
                    self._get_definition_record(): record[
                        self._get_definition_record()
                    ],
                },
            )

    def _add_default_values(
        self, env: typing.Any, values: dict[str, typing.Any]
    ) -> list[typing.Any] | dict[str, typing.Any]:
        properties_values = values.get(self.name) or {}

        if isinstance(properties_values, Property):
            properties_values = properties_values._values

        if not values.get(self._get_definition_record()):
            _debug.logic(
                "field.properties.defaults_skipped",
                model=self.model_name,
                field=self.name,
                reason="no_container",
            )
            return {}

        container_id = values[self._get_definition_record()]
        if not isinstance(container_id, int) and not hasattr(container_id, "_ids"):
            raise ValueError(f"Wrong container value {container_id!r}")

        if isinstance(container_id, int):
            current_model = env[self.model_name]
            definition_record_field = current_model._fields[self.definition_record]
            container_model_name = definition_record_field.comodel_name
            container_id = env[container_model_name].sudo().browse(container_id)

        properties_definition = container_id[self.definition_record_field]
        if not (
            properties_definition
            or (
                isinstance(properties_values, list)
                and any(d.get("definition_changed") for d in properties_values)
            )
        ):
            _debug.logic(
                "field.properties.defaults_skipped",
                model=self.model_name,
                field=self.name,
                reason="no_definition",
                container=container_id._name,
            )
            return {}

        assert isinstance(properties_values, (list, dict))
        if isinstance(properties_values, list):
            self._remove_display_name(properties_values)
            properties_list_values = properties_values
        else:
            properties_list_values = self._dict_to_list(
                properties_values, properties_definition
            )

        defaulted = 0  # debuglog
        for properties_value in properties_list_values:
            if properties_value.get("value") is None:
                property_name = properties_value.get("name")
                context_key = f"default_{self.name}.{property_name}"
                if property_name and context_key in env.context:
                    default = env.context[context_key]
                else:
                    default = properties_value.get("default")
                if default is not None:
                    properties_value["value"] = default
                    defaulted += 1  # debuglog

        _debug.logic(
            "field.properties.defaults_applied",
            model=self.model_name,
            field=self.name,
            container=container_id._name,
            properties=len(properties_list_values),
            defaulted=defaulted,
            given_as="list" if isinstance(properties_values, list) else "dict",
        )
        return properties_list_values

    def _get_properties_definition(
        self, record: ModelLike
    ) -> list[dict[str, typing.Any]] | None:
        assert self.definition_record is not None
        container = record[self.definition_record]
        if container:
            return container.sudo()[self.definition_record_field]
        return None

    @classmethod
    def _add_display_name(
        cls,
        values_list: list[dict[str, typing.Any]],
        env: typing.Any,
        value_keys: tuple[str, ...] = ("value", "default"),
    ) -> None:
        for property_definition in values_list:
            property_type = property_definition.get("type")
            property_model = property_definition.get("comodel")
            if not property_model:
                continue

            for value_key in value_keys:
                property_value = property_definition.get(value_key)

                if (
                    property_type == "many2one"
                    and property_value
                    and isinstance(property_value, int)
                ):
                    try:
                        display_name = (
                            env[property_model].browse(property_value).display_name
                        )
                        property_definition[value_key] = (
                            property_value,
                            display_name,
                        )
                    except AccessError:
                        property_definition[value_key] = (property_value, None)
                    except MissingError:
                        property_definition[value_key] = False

                elif (
                    property_type == "many2many"
                    and property_value
                    and is_list_of(property_value, int)
                ):
                    property_definition[value_key] = []
                    records = env[property_model].browse(property_value)
                    for record in records:
                        try:
                            property_definition[value_key].append(
                                (record.id, record.display_name)
                            )
                        except AccessError:
                            property_definition[value_key].append((record.id, None))
                        except MissingError:
                            continue

    @classmethod
    def _remove_display_name(
        cls,
        values_list: list[dict[str, typing.Any]],
        value_key: str = "value",
    ) -> None:
        for property_definition in values_list:
            if not isinstance(property_definition, dict) or not property_definition.get(
                "name"
            ):
                continue

            property_value = property_definition.get(value_key)
            if not property_value:
                continue

            property_type = property_definition.get("type")

            if property_type == "many2one" and has_list_types(
                property_value, [int, (str, NoneType)]
            ):
                property_definition[value_key] = property_value[0]

            elif property_type == "many2many":
                if is_list_of(property_value, (list, tuple)):
                    property_definition[value_key] = [
                        many2many_value[0] for many2many_value in property_value
                    ]

    @classmethod
    def _add_missing_names(cls, values_list: list[dict[str, typing.Any]]) -> None:
        generated = 0  # debuglog
        for definition in values_list:
            if definition.get("definition_changed") and not definition.get("name"):
                definition["name"] = str(uuid.uuid4()).replace("-", "")[:16]
                generated += 1  # debuglog
        if _debug.lifecycle.enabled and generated:
            _debug.lifecycle(
                "field.properties.names_generated",
                generated=generated,
                properties=len(values_list),
            )

    @classmethod
    def _parse_json_types(
        cls,
        values_list: list[dict[str, typing.Any]],
        env: typing.Any,
        res_ids_per_model: dict[str, set[int]],
    ) -> None:
        for property_definition in values_list:
            property_value = property_definition.get("value")
            property_type = property_definition.get("type")
            res_model = property_definition.get("comodel") or ""

            if property_type not in cls.ALLOWED_TYPES:
                raise ValueError(f"Wrong property type {property_type!r}")

            if property_value is None:
                continue

            if property_type == "boolean":
                property_value = bool(property_value)

            elif property_type in ("char", "text") and not isinstance(
                property_value, str
            ):
                property_value = False

            elif property_value and property_type == "selection":
                options = property_definition.get("selection") or []
                options = {option[0] for option in options if option}
                if property_value not in options:
                    property_value = False

            elif property_value and property_type == "tags":
                all_tags = {tag[0] for tag in property_definition.get("tags") or ()}
                property_value = [tag for tag in property_value if tag in all_tags]

            elif property_type == "many2one":
                if (
                    not isinstance(property_value, int)
                    or res_model not in env
                    or property_value not in res_ids_per_model[res_model]
                ):
                    property_value = False

            elif property_type == "many2many":
                if not is_list_of(property_value, int):
                    property_value = []

                elif len(property_value) != len(set(property_value)):
                    property_value = list(dict.fromkeys(property_value))

                property_value = (
                    [
                        id_
                        for id_ in property_value
                        if id_ in res_ids_per_model[res_model]
                    ]
                    if res_model in env
                    else []
                )

            elif property_type == "html":
                property_value = (
                    property_definition["name"].endswith("_html") and property_value
                )

            if (
                _debug.logic.enabled
                and property_value in (False, [])
                and property_definition.get("value") not in (False, [], None)
            ):
                _debug.logic(
                    "field.properties.value_rejected",
                    property=property_definition.get("name"),
                    property_type=property_type,
                    comodel=res_model or None,
                )
            property_definition["value"] = property_value

    @classmethod
    def _list_to_dict(
        cls, values_list: list[dict[str, typing.Any]]
    ) -> dict[str, typing.Any]:
        if not is_list_of(values_list, dict):
            raise ValueError(f"Wrong properties value {values_list!r}")

        cls._add_missing_names(values_list)

        dict_value = {}
        for property_definition in values_list:
            property_value = property_definition.get("value")
            property_type = property_definition.get("type")
            property_model = property_definition.get("comodel")
            if property_value is None:
                continue

            if is_recordset(property_value):
                property_value = (
                    property_value.id
                    if property_type == "many2one"
                    else property_value.ids
                )
            if property_type not in ("integer", "float") or property_value != 0:
                property_value = property_value or False
            if (
                property_type in RELATIONAL_PROPERTY_TYPES
                and property_model
                and property_value
            ):
                if (
                    property_type == "many2many"
                    and property_value
                    and not is_list_of(property_value, int)
                ):
                    raise ValueError(f"Wrong many2many value {property_value!r}")

                if property_type == "many2one" and not isinstance(property_value, int):
                    raise ValueError(f"Wrong many2one value {property_value!r}")

            dict_value[property_definition["name"]] = property_value

        return dict_value

    @classmethod
    def _dict_to_list(
        cls,
        values_dict: dict[str, typing.Any],
        properties_definition: list[dict[str, typing.Any]],
    ) -> list[dict[str, typing.Any]]:
        if not is_list_of(properties_definition, dict):
            raise ValueError(f"Wrong properties value {properties_definition!r}")

        values_list = fast_clone(properties_definition)
        for property_definition in values_list:
            if property_definition["name"] in values_dict:
                property_definition["value"] = values_dict[property_definition["name"]]
            else:
                property_definition.pop("value", None)
        return values_list

    @override
    def get_expression_getter(self, field_expr: str) -> typing.Any:
        _fname, property_name = parse_field_expr(field_expr)
        if not property_name:
            raise ValueError(f"Missing property name for {self}")

        def get_property(record: BaseModel) -> typing.Any:
            property_value = self.__get__(
                record.with_context(property_selection_get_key=True)
            )
            value = property_value.get(property_name)
            if value:
                return value
            for definition in self._get_properties_definition(record) or ():
                if definition.get("name") == property_name:
                    break
            else:
                return value or False

            if not value and definition["type"] in RELATIONAL_PROPERTY_TYPES:
                return record.env.get(definition.get("comodel"))
            return value

        return get_property

    @override
    def filter_function(
        self, records: BaseModel, field_expr: str, operator: str, value: typing.Any
    ) -> typing.Any:
        getter = self.get_expression_getter(field_expr)
        relational = (
            operator == "in"
            and isinstance(value, COLLECTION_TYPES)
            and hasattr(getter(records[:1]), "_ids")
        )
        _debug.logic(
            "field.properties.filter_function",
            model=self.model_name,
            field_expr=field_expr,
            operator=operator,
            strategy="relational_domain"
            if relational or operator == "any" or isinstance(value, Domain)
            else "collection"
            if operator == "in" and isinstance(value, COLLECTION_TYPES)
            else "scalar",
        )
        if operator == "any" or isinstance(value, Domain):
            domain = Domain(value).optimize(records)
            return lambda rec: getter(rec).filtered_domain(domain)
        if relational:
            # the same buckets as _property_in_to_sql: False is the unset
            # property, an id matches the record or one of the records
            match_unset = any(v is False for v in value)
            ids = [v for v in value if v is not False]
            domain = Domain("id", "in", ids).optimize(records) if ids else Domain.FALSE

            def matches_record(rec: BaseModel) -> bool:
                corecords = getter(rec)
                if not corecords:
                    return match_unset
                return bool(corecords.filtered_domain(domain))

            return matches_record

        if operator == "in" and isinstance(value, COLLECTION_TYPES):
            return self._filter_property_in(getter, value)
        return super().filter_function(records, field_expr, operator, value)

    @staticmethod
    def _filter_property_in(
        getter: abc.Callable[[BaseModel], typing.Any], value: abc.Collection
    ) -> abc.Callable[[BaseModel], bool]:
        # the same buckets as _property_in_to_sql: False is the unset property
        # (json false, null or no key), [True] alone means "set", and a value
        # matches a scalar or one item of a tags list
        values = list(value)
        if len(values) == 1 and values[0] is True:
            return lambda rec: not _is_unset(getter(rec))
        match_unset = any(v is False for v in values)
        values = [v for v in values if v is not False]

        def matches(rec: BaseModel) -> bool:
            rec_value = getter(rec)
            if _is_unset(rec_value):
                return match_unset
            items = rec_value if type(rec_value) is list else (rec_value,)
            return any(_same_value(v, item) for v in values for item in items)

        return matches

    def property_to_sql(
        self,
        field_sql: SQL,
        property_name: str,
        model: ModelLike,
        alias: str,
        query: Query,
    ) -> SQL:
        check_property_field_value_name(property_name)
        return SQL("(%s -> %s)", field_sql, property_name)

    @staticmethod
    def _property_in_to_sql(
        operator: str, value, sql_left: SQL, raw_sql_field: SQL, property_name: str
    ) -> SQL:
        assert isinstance(value, COLLECTION_TYPES)
        if len(value) == 1 and any(v is True for v in value):
            check_null_op_false = "!=" if operator == "in" else "="
            value = []
            operator = "in" if operator == "not in" else "not in"
        elif any(v is False for v in value):
            check_null_op_false = "=" if operator == "in" else "!="
            value = [v for v in value if v is not False]
        else:
            value = list(value)
            check_null_op_false = None

        sqls = []
        if check_null_op_false:
            sqls.append(
                SQL(
                    "%s%s'false'::jsonb",
                    sql_left,
                    SQL_OPERATORS[check_null_op_false],
                )
            )
            if check_null_op_false == "=":
                sqls.extend(_unset_property_sql(raw_sql_field, property_name))
        for one_value in value:
            sql_value = SQL("%s", json.dumps(one_value))
            sql_array = SQL("%s", json.dumps([one_value]))
            if operator == "in":
                sqls.append(
                    SQL(
                        "(%s = %s OR %s @> %s)",
                        sql_left,
                        sql_value,
                        sql_left,
                        sql_array,
                    )
                )
            else:
                sqls.append(
                    SQL(
                        "(%s != %s AND NOT %s @> %s)",
                        sql_left,
                        sql_value,
                        sql_left,
                        sql_array,
                    )
                )
        assert sqls, "No SQL generated for property"
        if operator == "not in" and check_null_op_false is None:
            # "not in" keeps the records without the property, as a column's
            # NOT IN keeps the NULLs; a NULL json value answers neither branch
            return SQL(
                "(%s OR %s)",
                SQL(" AND ").join(sqls),
                SQL(" OR ").join(_unset_property_sql(raw_sql_field, property_name)),
            )
        if len(sqls) == 1:
            return sqls[0]
        combine_sql = SQL(" OR ") if operator == "in" else SQL(" AND ")
        return SQL("(%s)", combine_sql.join(sqls))

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
        fname, property_name = parse_field_expr(field_expr)
        if not property_name:
            raise ValueError(f"Missing property name for {self}")
        raw_sql_field = model._field_to_sql(alias, fname, query)
        sql_left = model._field_to_sql(alias, field_expr, query)

        _debug.logic(
            "field.properties.condition_to_sql",
            model=model._name,
            field_expr=field_expr,
            operator=operator,
            shape="in"
            if operator in ("in", "not in")
            else "text"
            if isinstance(value, str) or operator.endswith("like")
            else "json",
        )
        if operator in ("in", "not in"):
            return self._property_in_to_sql(
                operator, value, sql_left, raw_sql_field, property_name
            )

        def unaccent(x):
            return x

        if operator.endswith("like"):
            if operator.endswith("ilike"):
                unaccent = model.env.registry.unaccent
            if "=" in operator:
                value = str(value)
            else:
                value = f"%{value}%"

        try:
            sql_operator = SQL_OPERATORS[operator]
        except KeyError:
            raise ValueError(f"Invalid operator {operator} for Properties") from None

        if isinstance(value, str):
            # ->> renders an unset property (json false) as the text 'false',
            # which LIKE '%a%' and < 'red' would match; only text compares
            sql_json = sql_left
            sql_left = SQL(
                "(CASE WHEN jsonb_typeof(%s) IN ('boolean', 'null')"
                " THEN NULL ELSE %s ->> %s END)",
                sql_json,
                raw_sql_field,
                property_name,
            )
            sql_right = SQL("%s", value)
            sql = SQL(
                "%s%s%s",
                unaccent(sql_left),
                sql_operator,
                unaccent(sql_right),
            )
            if operator in Domain.NEGATIVE_OPERATORS:
                sql = SQL("(%s OR %s IS NULL)", sql, sql_left)
            elif operator in PYTHON_INEQUALITY_OPERATOR:
                # a list or a number does not order against text
                sql = SQL("(jsonb_typeof(%s) = 'string' AND %s)", sql_json, sql)
            return sql

        sql_right = SQL("%s", json.dumps(value))
        sql = SQL("%s%s%s", sql_left, sql_operator, sql_right)
        if operator in PYTHON_INEQUALITY_OPERATOR and isinstance(value, int | float):
            # jsonb orders every boolean above every number: an unset
            # property (false) would satisfy size > 2
            json_type = "boolean" if isinstance(value, bool) else "number"
            sql = SQL("(jsonb_typeof(%s) = %s AND %s)", sql_left, json_type, sql)
        return sql


class Property(abc.Mapping):
    def __init__(
        self,
        values: dict[str, typing.Any],
        field: Properties,
        record: ModelLike,
    ) -> None:
        self._values = values
        self.record = record
        self.field = field
        self._definitions_by_name: dict[str, typing.Any] | None = None

    def _get_definitions(self) -> dict[str, typing.Any]:
        index = self._definitions_by_name
        if index is None:
            values = self.field.convert_to_read(
                self._values,
                self.record,
                use_display_name=False,
            )
            index = self._definitions_by_name = {prop["name"]: prop for prop in values}
            if _debug.perf.enabled:
                _debug.perf.count(
                    "field.properties.definitions_indexed",
                    model=getattr(self.field, "model_name", None),
                    field=getattr(self.field, "name", None),
                    record=getattr(self.record, "id", None),
                    definitions=len(index),
                    values=len(self._values),
                )
        return index

    def __iter__(self) -> typing.Iterator[str]:
        if not self.record:
            yield from self._values
            return
        definitions = self._get_definitions()
        for key in self._values:
            if key in definitions:
                yield key

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __eq__(self, other: object) -> bool:
        return self._values == (other._values if isinstance(other, Property) else other)

    def __getitem__(self, property_name: str) -> typing.Any:
        if not self.record:
            return False

        prop = self._get_definitions().get(property_name)
        if not prop:
            raise KeyError(property_name)

        if prop.get("type") in RELATIONAL_PROPERTY_TYPES and prop.get("comodel"):
            return self.record.env[prop.get("comodel")].browse(prop.get("value"))

        if prop.get("type") == "selection" and prop.get("value"):
            if self.record.env.context.get("property_selection_get_key"):
                return next(
                    (
                        sel[0]
                        for sel in prop.get("selection")
                        if sel[0] == prop["value"]
                    ),
                    False,
                )
            return next(
                (sel[1] for sel in prop.get("selection") if sel[0] == prop["value"]),
                False,
            )

        if prop.get("type") == "tags" and prop.get("value"):
            tags = prop.get("tags") or ()
            if self.record.env.context.get("property_selection_get_key"):
                return [tag[0] for tag in tags if tag[0] in prop["value"]]
            return ", ".join(tag[1] for tag in tags if tag[0] in prop["value"])

        value = prop.get("value")
        if prop.get("type") not in ("integer", "float") or value != 0:
            value = value or False
        return value

    def __hash__(self) -> int:
        return hash(
            frozendict(
                {
                    name: tuple(value) if isinstance(value, list) else value
                    for name, value in self._values.items()
                }
            )
        )


class PropertiesDefinition(Field):
    type = "properties_definition"
    cache_truthiness_matches = False
    _column_type = ("jsonb", "jsonb")
    copy = True
    readonly = False
    prefetch = True

    REQUIRED_KEYS = ("name", "type")
    ALLOWED_KEYS = (
        "name",
        "string",
        "type",
        "comodel",
        "default",
        "suffix",
        "selection",
        "tags",
        "domain",
        "view_in_cards",
        "fold_by_default",
        "currency_field",
    )
    PROPERTY_PARAMETERS_MAP = {
        "comodel": RELATIONAL_PROPERTY_TYPES,
        "currency_field": {"monetary"},
        "domain": RELATIONAL_PROPERTY_TYPES,
        "selection": {"selection"},
        "tags": {"tags"},
    }

    @override
    def convert_to_column(
        self,
        value: typing.Any,
        record: ModelLike,
        values: dict[str, typing.Any] | None = None,
        validate: bool = True,
    ) -> typing.Any:
        if not value:
            return None

        if isinstance(value, str):
            value = json.loads(value)

        if not isinstance(value, list):
            raise TypeError(f"Wrong properties definition type {type(value)!r}")

        if validate:
            Properties._remove_display_name(value, value_key="default")

            self._check_properties_definition(value, record.env)

        return PsycopgJson(record._convert_to_column_properties_definition(value))

    @override
    def convert_to_cache(
        self, value: typing.Any, record: ModelLike, validate: bool = True
    ) -> list[dict[str, typing.Any]] | None:
        if not value:
            return None

        if isinstance(value, list):
            value = json.dumps(value)

        if isinstance(value, str):
            value = json.loads(value)

        if not isinstance(value, list):
            raise TypeError(f"Wrong properties definition type {type(value)!r}")

        if validate:
            Properties._remove_display_name(value, value_key="default")

            self._check_properties_definition(value, record.env)

        return record._convert_to_cache_properties_definition(value)

    @override
    def convert_to_record(
        self, value: typing.Any, record: ModelLike
    ) -> list[dict[str, typing.Any]]:
        if not value:
            return []

        result = []

        for property_definition in value:
            if not all(property_definition.get(key) for key in self.REQUIRED_KEYS):
                continue

            property_definition = fast_clone(property_definition)

            type_ = property_definition.get("type")

            if type_ in RELATIONAL_PROPERTY_TYPES:
                property_model = property_definition.get("comodel")
                if property_model not in record.env:
                    property_definition["comodel"] = False
                    property_definition.pop("domain", None)
                    _debug.logic(
                        "field.properties_definition.comodel_dropped",
                        model=self.model_name,
                        field=self.name,
                        property=property_definition.get("name"),
                        comodel=property_model,
                    )
                elif property_domain := property_definition.get("domain"):
                    if len(property_domain) > 8192:
                        del property_definition["domain"]
                        _debug.logic(
                            "field.properties_definition.domain_dropped",
                            model=self.model_name,
                            field=self.name,
                            property=property_definition.get("name"),
                            reason="too_long",
                            length=len(property_domain),
                        )
                    else:
                        try:
                            dom = Domain(ast.literal_eval(property_domain))
                            model = record.env[property_model]
                            dom.check(model)
                        except (ValueError, SyntaxError, MemoryError) as exc:
                            del property_definition["domain"]
                            _debug.logic(
                                "field.properties_definition.domain_dropped",
                                model=self.model_name,
                                field=self.name,
                                property=property_definition.get("name"),
                                reason="invalid",
                                error=type(exc).__name__,
                            )

            elif type_ in ("selection", "tags"):
                property_definition[type_] = property_definition.get(type_) or []

            result.append(property_definition)

        return result

    @override
    def convert_to_read(
        self, value: typing.Any, record: ModelLike, use_display_name: bool = True
    ) -> typing.Any:
        if not value:
            return value

        if use_display_name:
            Properties._add_display_name(value, record.env, value_keys=("default",))

        return value

    @override
    def convert_to_write(self, value: typing.Any, record: ModelLike) -> typing.Any:
        return value

    def _check_property_keys(
        self, property_definition: dict, allowed_keys_set: set
    ) -> None:
        for property_parameter, allowed_types in self.PROPERTY_PARAMETERS_MAP.items():
            if (
                property_definition.get("type") not in allowed_types
                and property_parameter in property_definition
            ):
                raise ValueError(f"Invalid property parameter {property_parameter!r}")

        property_definition_keys = set(property_definition.keys())

        invalid_keys = property_definition_keys - allowed_keys_set
        if invalid_keys:
            raise ValueError(
                "Some key are not allowed for a properties definition [%s]."
                % ", ".join(invalid_keys),
            )

        missing_keys = [
            key for key in self.REQUIRED_KEYS if not property_definition.get(key)
        ]
        if missing_keys:
            raise ValueError(
                "Some keys are missing or empty for a properties definition [%s]."
                % ", ".join(missing_keys),
            )

    @staticmethod
    def _check_property_name(property_definition: dict, properties_names: set) -> None:
        check_property_field_value_name(property_definition["name"])

        property_type = property_definition["type"]
        property_name = property_definition["name"]
        if property_name in properties_names:
            raise ValueError(f"The property name {property_name!r} is duplicated.")
        properties_names.add(property_name)

        if property_type == "html" and not property_name.endswith("_html"):
            msg = "HTML property name should end with `_html`."
            raise ValueError(msg)

        if property_type != "html" and property_name.endswith("_html"):
            msg = "Only HTML properties can have the `_html` suffix."
            raise ValueError(msg)

        if property_type not in Properties.ALLOWED_TYPES:
            raise ValueError(f"Wrong property type {property_type!r}.")

        if property_type == "html" and (default := property_definition.get("default")):
            property_definition["default"] = html_sanitize(
                default, **Properties.HTML_SANITIZE_OPTIONS
            )

    @staticmethod
    def _check_property_options(property_definition: dict, env: typing.Any) -> None:
        model = property_definition.get("comodel")
        if model and (
            model not in env or env[model].is_transient() or env[model]._abstract
        ):
            raise ValueError(f"Invalid model name {model!r}")

        property_selection = property_definition.get("selection")
        if property_selection:
            if not is_list_of(property_selection, (list, tuple)) or not all(
                len(selection) == 2 for selection in property_selection
            ):
                raise ValueError(f"Wrong options {property_selection!r}.")

            all_options = [option[0] for option in property_selection]
            if len(all_options) != len(set(all_options)):
                duplicated = set(
                    filter(lambda x: all_options.count(x) > 1, all_options)
                )
                raise ValueError(
                    f"Some options are duplicated: {', '.join(duplicated)}."
                )

        property_tags = property_definition.get("tags")
        if property_tags:
            if not is_list_of(property_tags, (list, tuple)) or not all(
                len(tag) == 3 and isinstance(tag[2], int) for tag in property_tags
            ):
                raise ValueError(f"Wrong tags definition {property_tags!r}.")

            all_tags = [tag[0] for tag in property_tags]
            if len(all_tags) != len(set(all_tags)):
                duplicated = set(filter(lambda x: all_tags.count(x) > 1, all_tags))
                raise ValueError(f"Some tags are duplicated: {', '.join(duplicated)}.")

    def _check_properties_definition(
        self, properties_definition: list[dict[str, typing.Any]], env: typing.Any
    ) -> None:
        allowed_keys = (
            self.ALLOWED_KEYS
            + env["base"]._get_additional_allowed_keys_properties_definition()
        )
        allowed_keys_set = set(allowed_keys)

        env["base"]._check_properties_definition(properties_definition, self)

        properties_names: set[str] = set()

        for property_definition in properties_definition:
            self._check_property_keys(property_definition, allowed_keys_set)
            self._check_property_name(property_definition, properties_names)
            self._check_property_options(property_definition, env)
        _debug.pipeline(
            "field.properties_definition.checked",
            model=self.model_name,
            field=self.name,
            definitions=len(properties_definition),
            allowed_keys=len(allowed_keys_set),
        )
