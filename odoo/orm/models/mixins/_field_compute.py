from __future__ import annotations

import typing

from odoo.libs.debug_log import DebugLog

from ...fields.base import call_hook
from ._model_stubs import _ModelStubs

if typing.TYPE_CHECKING:
    from ...fields.base import Field

_debug = DebugLog(__name__)


class _FieldComputeMixin(_ModelStubs):
    __slots__ = ()

    def _compute_field_value(self, field: Field, validate: bool = True) -> None:
        if _debug.perf.enabled:
            with _debug.perf(
                "compute.field",
                cr=getattr(self.env, "cr", None),
                model=field.model_name,
                field=field.name,
                records=len(self),
                validate=validate,
            ):
                call_hook(field.compute, self)
        else:
            call_hook(field.compute, self)

        if validate:
            self._check_computed(field)

    def _check_computed(self, field: Field) -> None:
        if field.store and any(self._ids):
            fnames = [f.name for f in self.pool.field_computed[field]]
            if _debug.pipeline.enabled:
                _debug.pipeline(
                    "compute.checked",
                    model=field.model_name,
                    field=field.name,
                    records=len(self),
                    fields=len(fnames),
                )
            self.filtered("id")._check_fields(fnames)
