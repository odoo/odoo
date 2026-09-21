from __future__ import annotations

import datetime
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from typing import Any

from odoo.libs.documents import to_date, to_datetime, to_float

OPTIMIZE_FOR = ("balanced", "cost", "accuracy", "speed")

TYPES: dict[str, type | tuple[type, ...]] = {
    "str": str,
    "float": (int, float),
    "int": int,
    "bool": bool,
    "date": (datetime.date, str),
    "datetime": (datetime.datetime, str),
    "list": list,
    "dict": dict,
}


@dataclass(frozen=True)
class FieldSpec:
    type: str = "str"
    required: bool = False
    help: str = ""
    items: dict[str, FieldSpec] | None = None
    choices: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.type not in TYPES:
            raise ValueError(
                f"Unknown field type {self.type!r}; expected one of "
                f"{', '.join(sorted(TYPES))}"
            )
        if self.choices and self.type != "str":
            raise ValueError(f"Only a str offers choices; this one is a {self.type!r}")
        if self.items is None:
            return
        if self.type != "list":
            raise ValueError(f"Only a list declares items; this one is a {self.type!r}")
        if not self.items:
            raise ValueError("A list that declares items must name at least one")
        nested = sorted(k for k, spec in self.items.items() if spec.items is not None)
        if nested:
            raise ValueError(
                f"A row is one level deep; {', '.join(nested)} declares items of "
                "its own"
            )

    def accepts(self, value: Any) -> bool:
        if value is None:
            return True
        if self.type in ("int", "float") and isinstance(value, bool):
            return False
        return isinstance(value, TYPES[self.type])

    def coerce(self, value: Any) -> Any:
        if value is None:
            return None
        if self.type == "datetime":
            return _as_utc(to_datetime(value)).isoformat(sep=" ", timespec="seconds")
        if self.choices:
            return self._choice(value)
        if self.type == "date":
            # Never short-circuited on `accepts`, which passes any str -- that
            # looseness is the whole reason a date needs coercing, and
            # returning "12/03/2026" untouched is how an unparseable date
            # reaches the consistency rules and raises inside one.
            return to_date(value).isoformat()
        if self.type in ("float", "int"):
            if isinstance(value, bool):
                raise ValueError(f"{value!r} is a boolean, not a number")
            if isinstance(value, (int, float)):
                return value
            number = to_float(value)
            if self.type == "int":
                if number != int(number):
                    raise ValueError(f"{value!r} is not a whole number")
                return int(number)
            return number
        if not self.accepts(value):
            raise ValueError(f"{value!r} is not a {self.type}")
        if self.type == "list" and self.items is not None:
            rows = [row for row in map(self._coerce_row, value) if row is not None]
            # None and not [], so a required list whose every row was unreadable
            # is reported missing. `Schema.missing` asks `is None`, and an empty
            # list satisfies a requirement while carrying nothing.
            return rows or None
        return value

    def _choice(self, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{value!r} is not one of {', '.join(self.choices)}")
        wanted = value.strip().casefold()
        for choice in self.choices:
            if choice.casefold() == wanted:
                return choice
        raise ValueError(f"{value!r} is not one of {', '.join(self.choices)}")

    def _coerce_row(self, row: Any) -> dict[str, Any] | None:
        # A row that cannot be read is dropped and the rest of the list is kept.
        # Raising instead would discard every row because one of them was
        # unreadable, and send the cascade back to a more expensive strategy for
        # a list it had already read.
        if not isinstance(row, dict):
            row = self._row_of(row)
            if row is None:
                return None
        read: dict[str, Any] = {k: v for k, v in row.items() if k not in self.items}
        for name, spec in self.items.items():
            try:
                value = spec.coerce(row.get(name))
            except TypeError, ValueError:
                value = None
            if value is None and spec.required:
                return None
            if value is not None:
                read[name] = value
        return read or None

    def _row_of(self, value: Any) -> dict[str, Any] | None:
        # A skill is "Python" as readily as {"name": "Python"}, and a row with
        # exactly one required key has exactly one place the bare value can go.
        # With two, there is no such place and guessing one would be the
        # unwritten contract this declaration exists to end.
        if value is None:
            return None
        required = [name for name, spec in self.items.items() if spec.required]
        if len(required) != 1:
            return None
        return {required[0]: value}


@dataclass(frozen=True)
class Rule:
    name: str
    fields: tuple[str, ...]
    check: Callable[[dict[str, Any]], bool]
    message: str = ""

    def holds(self, values: dict[str, Any]) -> bool:
        if any(values.get(name) is None for name in self.fields):
            return True
        return bool(self.check(values))


@dataclass(frozen=True)
class Schema:
    name: str
    fields: dict[str, FieldSpec] = field(default_factory=dict)
    rules: tuple[Rule, ...] = ()
    instructions: str = ""
    optimize_for: str = "cost"
    purpose: str = ""

    def __post_init__(self) -> None:
        if self.optimize_for not in OPTIMIZE_FOR:
            raise ValueError(
                f"Unknown optimization {self.optimize_for!r}; expected one of "
                f"{', '.join(OPTIMIZE_FOR)}"
            )

    @property
    def ml_purpose(self) -> str:
        return self.purpose or f"extract.{self.name}"

    @property
    def required(self) -> tuple[str, ...]:
        return tuple(n for n, spec in self.fields.items() if spec.required)

    def missing(self, values: dict[str, Any]) -> tuple[str, ...]:
        return tuple(n for n in self.required if values.get(n) is None)

    def violations(self, values: dict[str, Any]) -> tuple[str, ...]:
        return tuple(rule.name for rule in self.rules if not rule.holds(values))


JSON_TYPES = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "date": "string",
    "datetime": "string",
    "list": "array",
    "dict": "object",
}
JSON_FORMATS = {"date": "date", "datetime": "date-time"}


def json_schema(schema: Schema, names: Iterable[str] = ()) -> dict[str, Any]:
    return _json_object(
        {name: schema.fields[name] for name in select_fields(schema, names)},
        nullable_required=True,
    )


def select_fields(schema: Schema, names: Iterable[str] = ()) -> tuple[str, ...]:
    known = tuple(name for name in names if name in schema.fields)
    return known or tuple(schema.fields)


def _json_object(specs: dict[str, FieldSpec], nullable_required: bool) -> dict:
    return {
        "type": "object",
        "properties": {
            name: _json_node(spec, nullable=nullable_required or not spec.required)
            for name, spec in specs.items()
        },
        "required": list(specs),
        "additionalProperties": False,
    }


def _json_node(spec: FieldSpec, nullable: bool) -> dict[str, Any]:
    kind = JSON_TYPES[spec.type]
    node: dict[str, Any] = {"type": [kind, "null"] if nullable else kind}
    if spec.type in JSON_FORMATS:
        node["format"] = JSON_FORMATS[spec.type]
    if spec.choices:
        node["enum"] = [*spec.choices, None] if nullable else list(spec.choices)
    if spec.items:
        node["items"] = _json_object(spec.items, nullable_required=False)
    if spec.help:
        node["description"] = spec.help
    return node


_SCHEMAS: dict[str, Schema] = {}


def register_schema(
    name: str,
    fields: dict[str, FieldSpec],
    rules: Iterable[Rule] = (),
    *,
    instructions: str = "",
    optimize_for: str = "cost",
    purpose: str = "",
) -> Schema:
    if name in _SCHEMAS:
        raise ValueError(f"Schema {name!r} is already registered")
    _SCHEMAS[name] = Schema(
        name=name,
        fields=dict(fields),
        rules=tuple(rules),
        instructions=instructions,
        optimize_for=optimize_for,
        purpose=purpose,
    )
    return _SCHEMAS[name]


def extend_schema(
    name: str,
    fields: dict[str, FieldSpec] | None = None,
    rules: Iterable[Rule] = (),
) -> Schema:
    schema = get_schema(name)
    added = dict(fields or {})
    clashing = sorted(set(added) & set(schema.fields))
    if clashing:
        raise ValueError(
            f"Schema {name!r} already declares {', '.join(clashing)}; "
            "extend with new fields or change the declaration"
        )
    _SCHEMAS[name] = replace(
        schema,
        fields={**schema.fields, **added},
        rules=schema.rules + tuple(rules),
    )
    return _SCHEMAS[name]


def get_schema(name: str) -> Schema:
    try:
        return _SCHEMAS[name]
    except KeyError:
        raise ValueError(
            f"Unknown document type {name!r}; registered: "
            f"{', '.join(sorted(_SCHEMAS)) or 'none'}"
        ) from None


def known_schemas() -> tuple[str, ...]:
    return tuple(sorted(_SCHEMAS))


def sums_to(
    name: str, parts: Iterable[str], total: str, tolerance: float = 0.01
) -> Rule:
    parts = tuple(parts)

    def _check(values: dict[str, Any]) -> bool:
        return abs(sum(values[p] for p in parts) - values[total]) <= tolerance

    return Rule(
        name=name,
        fields=(*parts, total),
        check=_check,
        message=f"{' + '.join(parts)} should equal {total}",
    )


def not_after(name: str, earlier: str, later: str) -> Rule:

    def _check(values: dict[str, Any]) -> bool:
        return _as_date(values[earlier]) <= _as_date(values[later])

    return Rule(
        name=name,
        fields=(earlier, later),
        check=_check,
        message=f"{earlier} should not be after {later}",
    )


def _as_date(value: datetime.date | str) -> datetime.date:
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value)[:10])


def _as_utc(value: datetime.datetime) -> datetime.datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(datetime.UTC).replace(tzinfo=None)
