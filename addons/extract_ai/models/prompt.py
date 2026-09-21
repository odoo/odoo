from __future__ import annotations

from typing import Any, NamedTuple

from odoo.addons.extract.tools.schema import (
    FieldSpec,
    Schema,
    json_schema,
    select_fields,
)

RULES = (
    "Use null for anything the document does not state.",
    "Never invent a value, and never carry one over from another document.",
    "Copy numbers exactly as printed, without rounding or reformatting.",
    "Dates as YYYY-MM-DD; date-times as YYYY-MM-DD HH:MM:SS.",
    "Where a field lists its values, answer with one of them or null.",
)


class ExtractionPrompt(NamedTuple):
    system: str
    prompt: str
    response_schema: dict[str, Any]


def _note(spec: FieldSpec) -> str:
    note = spec.help or ""
    if spec.required:
        note = f"{note} (required)".strip()
    if spec.choices:
        note = f"{note} -- one of: {', '.join(spec.choices)}".strip(" -")
    if spec.items:
        required = [n for n, item in spec.items.items() if item.required]
        if required:
            note = (
                f"{note} -- a row without {' and '.join(required)} is not a row"
            ).strip(" -")
    return note


def _describe(schema: Schema, names: tuple[str, ...]) -> list[str]:
    lines = []
    for name in names:
        spec = schema.fields[name]
        note = _note(spec)
        if note:
            lines.append(f"- {name}: {note}")
        for item_name, item in (spec.items or {}).items():
            item_note = _note(item)
            if item_note:
                lines.append(f"  - {name}.{item_name}: {item_note}")
    return lines


def prepare_prompt(schema: Schema, wanted: tuple[str, ...] = ()) -> ExtractionPrompt:
    names = select_fields(schema, wanted)
    system = "\n".join(
        part
        for part in (
            schema.instructions,
            "Answer with the requested JSON object only.",
            *(f"- {rule}" for rule in RULES),
        )
        if part
    )
    described = _describe(schema, names)
    checks = [
        f"- {rule.message}"
        for rule in schema.rules
        if rule.message and set(rule.fields) & set(names)
    ]
    parts = [f"Read this {schema.name.replace('_', ' ')}."]
    if described:
        parts += ["", "Fields:", *described]
    if checks:
        parts += ["", "These must hold, and are how the answer is checked:", *checks]
    return ExtractionPrompt(system, "\n".join(parts), json_schema(schema, names))
