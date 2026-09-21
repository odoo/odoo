import typing
import warnings
from collections.abc import Callable, Iterable, Iterator

from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import SENTINEL, unique

from ..primitives import STATE_FIELD

if typing.TYPE_CHECKING:
    from .._typing import BaseModel, ModelClass
    from ..runtime import Registry
    from .base import Field

_debug = DebugLog(__name__)


COMPANY_DEPENDENT_FIELDS: tuple[str, ...] = (
    "char",
    "float",
    "boolean",
    "integer",
    "text",
    "many2one",
    "date",
    "datetime",
    "selection",
    "html",
)


def resolve_mro(
    model: BaseModel, name: str, predicate: Callable[[typing.Any], bool]
) -> list[typing.Any]:
    result = []
    for cls in model._model_classes__:
        value = cls.__dict__.get(name, SENTINEL)
        if value is SENTINEL:
            continue
        if not predicate(value):
            break
        result.append(value)
    return result


def _normalize_computed_attrs(attrs: dict) -> None:
    if attrs.get("related"):
        attrs["store"] = attrs.get("store", False)
        attrs["compute_sudo"] = attrs.get(
            "compute_sudo", attrs.get("related_sudo", True)
        )
        attrs["copy"] = attrs.get("copy", False)
        attrs["readonly"] = attrs.get("readonly", True)
    elif attrs.get("compute"):
        attrs["store"] = store = attrs.get("store", False)
        attrs["compute_sudo"] = attrs.get("compute_sudo", store)
        if not (attrs["store"] and not attrs.get("readonly", True)):
            attrs["copy"] = attrs.get("copy", False)
        attrs["readonly"] = attrs.get("readonly", not attrs.get("inverse"))


def _warn_precompute_attrs(field: Field, attrs: dict) -> None:
    if attrs.get("precompute"):
        if not attrs.get("compute") and not attrs.get("related"):
            warnings.warn(
                f"precompute attribute doesn't make any sense on non computed field {field}",
                stacklevel=1,
            )
            attrs["precompute"] = False
            _debug.logic(
                "field.setup.precompute_dropped",
                model=field.model_name,
                field=field.name,
                reason="not_computed",
            )
        elif not attrs.get("store"):
            warnings.warn(
                f"precompute attribute has no impact on non stored field {field}",
                stacklevel=1,
            )
            attrs["precompute"] = False
            _debug.logic(
                "field.setup.precompute_dropped",
                model=field.model_name,
                field=field.name,
                reason="not_stored",
            )


def _normalize_company_dependent_attrs(field: Field, attrs: dict) -> None:
    if attrs.get("company_dependent"):
        if attrs.get("required"):
            warnings.warn(
                f"company_dependent field {field} cannot be required",
                stacklevel=1,
            )
        if attrs.get("translate"):
            warnings.warn(
                f"company_dependent field {field} cannot be translated",
                stacklevel=1,
            )
        if field.type not in COMPANY_DEPENDENT_FIELDS:
            warnings.warn(
                f"company_dependent field {field} is not one of the allowed types {COMPANY_DEPENDENT_FIELDS}",
                stacklevel=1,
            )
        attrs["copy"] = attrs.get("copy", False)
        attrs["index"] = attrs.get("index", "btree_not_null")
        attrs["prefetch"] = attrs.get("prefetch", "company_dependent")
        attrs["_depends_context"] = ("company",)
        _debug.logic(
            "field.setup.company_dependent",
            model=field.model_name,
            field=field.name,
            type=field.type,
            index=attrs["index"],
            allowed_type=field.type in COMPANY_DEPENDENT_FIELDS,
        )


def _normalize_depends_attrs(field: Field, attrs: dict) -> None:
    if "depends" in attrs:
        depends = tuple(attrs.pop("depends"))
        for dep in depends:
            if "id" in dep.split("."):
                raise ValueError(f"Field {field} cannot depend on field 'id'.")
        attrs["_depends"] = depends
    if "depends_context" in attrs:
        depends_context = tuple(attrs.pop("depends_context"))
        if attrs.get("company_dependent") and "company" not in depends_context:
            depends_context = ("company", *depends_context)
        attrs["_depends_context"] = depends_context


def get_attrs(
    field: Field, model_class: ModelClass, name: str
) -> dict[str, typing.Any]:
    attrs: dict[str, typing.Any] = {}
    modules: list[str] = []
    for base in field._args__.get("_base_fields__", ()):
        if not isinstance(field, type(base)):
            _debug.logic(
                "field.setup.base_attrs_dropped",
                model=model_class._name,
                field=name,
                base_type=type(base).__name__,
                type=type(field).__name__,
            )
            attrs.clear()
            modules.clear()
            continue
        attrs.update(base._args__)
        if base._module:
            modules.append(base._module)
    attrs.update(field._args__)
    if field._module:
        modules.append(field._module)

    attrs["model_name"] = model_class._name
    attrs["name"] = name
    attrs["_module"] = modules[-1] if modules else None
    attrs["_modules"] = tuple(unique(modules) if len(modules) > 1 else modules)

    if name == STATE_FIELD:
        attrs["copy"] = attrs.get("copy", False)
    _normalize_computed_attrs(attrs)
    _warn_precompute_attrs(field, attrs)
    _normalize_company_dependent_attrs(field, attrs)
    _normalize_depends_attrs(field, attrs)

    if "group_operator" in attrs:
        warnings.warn(
            "Since Odoo 18, 'group_operator' is deprecated, use 'aggregator' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        attrs["aggregator"] = attrs.pop("group_operator")

    return attrs


def get_depends(field: Field, model: BaseModel) -> tuple[Iterable[str], Iterable[str]]:
    if field._depends is not None:
        return field._depends, field._depends_context or ()

    if field.related:
        if field._depends_context is not None:
            depends_context = field._depends_context
        else:
            depends_context = []
            step_model_name = model._name
            for step_name in field.related.split("."):
                step_model = model.env[step_model_name]
                step = step_model._fields[step_name]
                depends_context.extend(step.get_depends(step_model)[1])
                step_model_name = step.comodel_name
            depends_context = tuple(unique(depends_context))
            if _debug.logic.enabled and depends_context:
                _debug.logic(
                    "field.setup.related_depends_context",
                    model=field.model_name,
                    field=field.name,
                    related=field.related,
                    depends_context=list(depends_context),
                )
        return [field.related], depends_context

    if not field.compute:
        return (), field._depends_context or ()

    if isinstance(field.compute, str):
        funcs = resolve_mro(model, field.compute, callable)
    else:
        funcs = [field.compute]

    depends: list[str] = []
    depends_context = list(field._depends_context or ())
    for func in funcs:
        deps = getattr(func, "_depends", ())
        depends.extend(deps(model) if callable(deps) else deps)
        depends_context.extend(getattr(func, "_depends_context", ()))

    return list(unique(depends)), list(unique(depends_context))


def resolve_depends(field: Field, registry: Registry) -> Iterator[tuple[Field, ...]]:
    Model0 = registry[field.model_name]

    for dotnames in registry.field_depends[field]:
        field_seq: list[Field] = []
        model_name: str | None = field.model_name
        check_precompute = field.precompute

        for index, fname in enumerate(dotnames.split(".")):
            if not model_name:
                raise ValueError(
                    f"Wrong dependency '{dotnames}' of field {field}: "
                    f"'{field_seq[-1].name}' is not relational, so the path "
                    f"cannot continue with '{fname}'."
                )
            Model = registry[model_name]
            if Model0._transient and not Model._transient:
                _debug.logic(
                    "field.depends.transient_path_cut",
                    model=field.model_name,
                    field=field.name,
                    path=dotnames,
                    at=model_name,
                )
                break

            try:
                step = Model._fields[fname]
            except KeyError:
                raise ValueError(
                    f"Wrong @depends on '{field.compute}' (compute method of field {field}). "
                    f"Dependency field '{fname}' not found in model {model_name}."
                ) from None
            if step is field and index and not field.recursive:
                field.recursive = True
                _debug.logic(
                    "field.depends.recursive_inferred",
                    model=field.model_name,
                    field=field.name,
                    path=dotnames,
                )
                warnings.warn(
                    f"Field {field} should be declared with recursive=True",
                    stacklevel=1,
                )

            if check_precompute and step.store and step.compute and not step.precompute:
                raise ValueError(
                    f"Field {field} cannot be precomputed as it depends on non-precomputed field {step}"
                )

            if field_seq and not field_seq[-1]._description_searchable:
                warnings.warn(
                    f"Field {field_seq[-1]!r} in dependency of {field} should be searchable. "
                    f"This is necessary to determine which records to recompute when {step} is modified. "
                    f"You should either make the field searchable, or simplify the field dependency.",
                    stacklevel=1,
                )

            field_seq.append(step)

            if not (step is field and not index):
                yield tuple(field_seq)

            if step.is_one2many:
                for inv_field in registry.field_inverses[step]:
                    yield tuple(field_seq) + (inv_field,)

            if check_precompute and step.is_many2one:
                check_precompute = False

            model_name = step.comodel_name
