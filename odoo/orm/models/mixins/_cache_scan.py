import typing

if typing.TYPE_CHECKING:
    from collections.abc import MutableMapping

    from ..._typing import IdType
    from ...fields.base import Field
    from ...runtime import Environment


def as_scannable_cache(
    field_cache: MutableMapping[IdType, typing.Any],
) -> dict[IdType, typing.Any]:
    return typing.cast("dict[IdType, typing.Any]", field_cache)


def is_cache_detached(field: Field, env: Environment, captured: object) -> bool:
    return field._get_cache(env) is not captured


def has_lang_dict_cache(field: Field, env: Environment) -> bool:
    return callable(field.translate) and bool(env.context.get("prefetch_langs"))


def can_scan_identity(field: Field) -> bool:
    return field.cache_is_record_value and not callable(field.translate)


def can_scan_truthy(field: Field) -> bool:
    return field.cache_truthiness_matches and not callable(field.translate)


def can_scan_sorted(field: Field) -> bool:
    return field.cache_is_orderable and not callable(field.translate)


def can_scan_read(field: Field) -> bool:
    return field.store and field.cache_is_read_value and not callable(field.translate)
