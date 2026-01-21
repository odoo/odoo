# ruff: noqa: PLC0415 (import in function not at top-level)
from __future__ import annotations

from shutil import copyfileobj
from types import CodeType

from werkzeug.datastructures import FileStorage, MultiDict
from werkzeug.routing import Rule
from werkzeug.wrappers import Request, Response

Rule_get_func_code = hasattr(Rule, '_get_func_code') and Rule._get_func_code


def patch_module():
    from odoo.tools.json import scriptsafe
    Request.json_module = Response.json_module = scriptsafe

    FileStorage.save = lambda self, dst, buffer_size=(1 << 20): copyfileobj(self.stream, dst, buffer_size)

    def _multidict_deepcopy(self, memo=None):
        return orig_deepcopy(self)

    orig_deepcopy = MultiDict.deepcopy
    MultiDict.deepcopy = _multidict_deepcopy

    if Rule_get_func_code:
        @staticmethod
        def _get_func_code(code, name):
            assert isinstance(code, CodeType)
            return Rule_get_func_code(code, name)
        Rule._get_func_code = _get_func_code
