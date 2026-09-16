from __future__ import annotations

import dis
import typing
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from opcode import opmap

from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_debug = DebugLog(__name__)


def _opnames(*names: str) -> frozenset[str]:
    if missing := sorted(n for n in names if n not in opmap):
        raise RuntimeError(
            f"depends_audit names opcode(s) {', '.join(missing)}, which do not "
            f"exist on this interpreter. Re-derive the sets against it: "
            f"silently dropping one narrows the analysis."
        )
    return frozenset(names)


_ATTR_ACCESS = _opnames("LOAD_ATTR", "STORE_ATTR")

_RECEIVER_LOAD = _opnames(
    "LOAD_ATTR",
    "LOAD_FAST",
    "LOAD_FAST_BORROW",
    "LOAD_FAST_CHECK",
    "LOAD_FAST_LOAD_FAST",
    "LOAD_FAST_BORROW_LOAD_FAST_BORROW",
    "LOAD_GLOBAL",
    "LOAD_DEREF",
    "LOAD_NAME",
)

_FOREIGN_ROOTS = frozenset({"env"})

_NEVER_A_DEPENDENCY = frozenset({"id"})


@dataclass(frozen=True)
class DependsFinding:
    model_name: str
    field_name: str
    reads: tuple[str, ...]
    stored: bool
    declared: tuple[str, ...] = dataclass_field(default=())

    @property
    def label(self) -> str:
        return f"{self.model_name}.{self.field_name}"

    def __str__(self) -> str:
        return (
            f"{self.label} computes without depending on "
            f"{', '.join(self.reads)}"
            f"{' (stored)' if self.stored else ''}"
        )


def _loaded_name(instruction: dis.Instruction) -> str | None:
    argval = instruction.argval
    if isinstance(argval, tuple):
        return argval[-1] if argval else None
    return argval if isinstance(argval, str) else None


def accessed_attribute_names(func: Callable) -> set[str]:
    names: set[str] = set()
    code = getattr(func, "__code__", None)
    if code is None:
        return names
    todo = [code]
    while todo:
        current = todo.pop()
        instructions = list(dis.get_instructions(current))
        foreign: set[int] = set()
        for index, instruction in enumerate(instructions):
            if instruction.opname not in _ATTR_ACCESS:
                continue
            previous = instructions[index - 1] if index else None
            if previous is None:
                if isinstance(instruction.argval, str):
                    names.add(instruction.argval)
                continue
            previous_name = _loaded_name(previous)
            if previous.opname in _RECEIVER_LOAD and previous_name in _FOREIGN_ROOTS:
                foreign.add(index)
                continue
            if index - 1 in foreign:
                foreign.add(index)
                continue
            if instruction.argval in _FOREIGN_ROOTS:
                foreign.add(index)
                continue
            if isinstance(instruction.argval, str):
                names.add(instruction.argval)
        todo.extend(c for c in current.co_consts if hasattr(c, "co_names"))
    return names


def _get_functions(field: typing.Any, model_class: typing.Any) -> list[Callable]:
    compute = field.compute
    if not compute:
        return []
    if not isinstance(compute, str):
        return [compute]
    from odoo.orm.fields.base import resolve_mro

    return resolve_mro(model_class, compute, callable)


def audit_field(
    registry: typing.Any, model_class: typing.Any, field: typing.Any
) -> DependsFinding | None:
    functions = _get_functions(field, model_class)
    if not functions:
        return None

    accessed: set[str] = set()
    for function in functions:
        accessed |= accessed_attribute_names(function)

    declared = {path.split(".")[0] for path in registry.field_depends.get(field, ())}
    computed_together = {
        other.name for other in registry.field_computed.get(field, [field])
    }

    reads = (
        (accessed & set(model_class._fields))
        - declared
        - computed_together
        - _NEVER_A_DEPENDENCY
    )
    if not reads:
        return None
    return DependsFinding(
        model_name=field.model_name,
        field_name=field.name,
        reads=tuple(sorted(reads)),
        stored=bool(field.store),
        declared=tuple(sorted(declared)),
    )


def audit_registry(
    registry: typing.Any,
    *,
    only_without_dependencies: bool = True,
    include_stored: bool = False,
) -> Iterator[DependsFinding]:
    registry._get_field_triggers()
    audited = findings = 0  # debuglog
    for model_class in registry.models.values():
        if model_class._abstract:
            continue
        for field in model_class._fields.values():
            if not field.compute:
                continue
            if field.related or field.is_properties:
                continue
            if field.store and not include_stored:
                continue
            if only_without_dependencies and (
                registry.field_depends.get(field)
                or any(
                    key != "access"
                    for key in registry.field_depends_context.get(field, ())
                )
            ):
                continue
            audited += 1  # debuglog
            finding = audit_field(registry, model_class, field)
            if finding is not None:
                findings += 1  # debuglog
                _debug.logic(
                    "depends_audit.finding",
                    model=finding.model_name,
                    field=finding.field_name,
                    reads=finding.reads,
                    stored=finding.stored,
                )
                yield finding
    _debug.pipeline(
        "depends_audit.done",
        models=len(registry.models),
        audited=audited,
        findings=findings,
        only_without_dependencies=only_without_dependencies,
        include_stored=include_stored,
    )
