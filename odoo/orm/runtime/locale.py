from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from .environment import Environment


class Locale:
    __slots__ = ()

    def installed_langs(self, env: Environment) -> list[str]:
        return [code for code, _name in env["res.lang"].get_installed()]

    def is_lang_installed(self, env: Environment, code: str) -> bool:
        return bool(env["res.lang"]._get_data(code=code))

    def decimal_precision(self, env: Environment, application: str) -> int:
        return env["decimal.precision"].get_precision(application)


LOCALE = Locale()
