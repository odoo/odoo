from types import CodeType

from werkzeug.datastructures import MultiDict
from werkzeug.routing import Rule
from werkzeug.wrappers import Request, Response


def patch_module():
    from odoo.tools.json import scriptsafe

    Request.json_module = Response.json_module = scriptsafe

    def _multidict_deepcopy(self, memo=None):
        return orig_deepcopy(self)

    orig_deepcopy = MultiDict.deepcopy
    MultiDict.deepcopy = _multidict_deepcopy

    _orig_get_func_code = Rule._get_func_code

    @staticmethod
    def _get_func_code(code, name):
        assert isinstance(code, CodeType)
        return _orig_get_func_code(code, name)

    Rule._get_func_code = _get_func_code
