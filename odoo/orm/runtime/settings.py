from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from .environment import Environment


class SystemSettings:
    __slots__ = ()

    def get(self, env: Environment, key: str, default: typing.Any = None) -> typing.Any:
        return env["ir.config_parameter"].sudo().get_param(key, default)


SYSTEM_SETTINGS = SystemSettings()
