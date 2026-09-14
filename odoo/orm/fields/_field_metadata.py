from __future__ import annotations

import functools
import typing

from ._field_stubs import _FieldStubs

if typing.TYPE_CHECKING:
    from .._typing import ModelLike
    from ..runtime import Environment
    from ._field_stubs import TranslateDialect


class _FieldMetadataMixin(_FieldStubs):
    __slots__ = ()

    name: str = ""
    model_name: str = ""

    store: bool = True
    translate: bool | TranslateDialect = False
    company_dependent: bool = False

    _column_type: tuple[str, str] | None = None

    @functools.cached_property
    def column_type(self) -> tuple[str, str] | None:
        return (
            ("jsonb", "jsonb")
            if self.company_dependent or self.translate
            else self._column_type
        )

    @functools.cached_property
    def is_column(self) -> bool:
        return bool(self.store and self.column_type)

    def _is_context_dependent(self, env: Environment) -> bool:
        return self in env._field_depends_context

    def _get_company_dependent_fallback_raw(self, records: ModelLike) -> typing.Any:
        env = records.env
        return env.registry.metaschema.company_dependent_fallbacks(
            env, records._name
        ).get(self.name)
