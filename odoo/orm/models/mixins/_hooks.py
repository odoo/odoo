from __future__ import annotations

import functools
import logging
from collections import defaultdict
from inspect import getmembers

from odoo.libs.debug_log import DebugLog

from ...helpers import get_or_create_class_memo
from ._model_stubs import _ModelStubs

_logger = logging.getLogger("odoo.models")
_debug = DebugLog(__name__)


class _HooksMixin(_ModelStubs):
    __slots__ = ()

    @property
    def _ondelete_methods(self) -> list:
        def is_ondelete(func):
            return callable(func) and hasattr(func, "_ondelete")

        cls = self.env.registry[self._name]
        return get_or_create_class_memo(
            cls,
            "_ondelete_methods__",
            lambda: [func for _, func in getmembers(cls, is_ondelete)],
        )

    @property
    def _onchange_methods(self) -> dict[str, list]:
        def is_onchange(func):
            return callable(func) and hasattr(func, "_onchange")

        cls = self.env.registry[self._name]

        def get_onchange_methods():
            methods = defaultdict(list)
            for _attr, func in getmembers(cls, is_onchange):
                missing = []
                for name in func._onchange:
                    if name in cls._fields:
                        methods[name].append(func)
                    else:
                        missing.append(name)
                if missing:
                    _logger.warning(
                        "@api.onchange%r parameters must be field names -> not valid: %s",
                        func._onchange,
                        missing,
                    )
                    _debug.logic(
                        "hooks.onchange_parameter_invalid",
                        model=cls._name,
                        method=_attr,
                        missing=missing,
                    )

            def onchange_default(field, self):
                value = field.convert_to_write(self[field.name], self)
                condition = f"{field.name}={value}"
                defaults = self.env.registry.metaschema.model_defaults(
                    self.env, self._name, condition
                )
                self.update(defaults)

            change_defaults = 0  # debuglog
            for name, field in cls._fields.items():
                if field.change_default:
                    change_defaults += 1  # debuglog
                    methods[name].append(functools.partial(onchange_default, field))

            _debug.perf.count(
                "hooks.onchange_collected",
                model=cls._name,
                fields=len(methods),
                change_defaults=change_defaults,
            )
            return dict(methods)

        return get_or_create_class_memo(
            cls, "_onchange_methods__", get_onchange_methods
        )
