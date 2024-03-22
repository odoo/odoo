import ast
import ctypes
import os
import logging
import string
from shutil import copyfileobj
from types import CodeType

_logger = logging.getLogger(__name__)

from werkzeug.datastructures import FileStorage
from werkzeug.routing import Rule
from werkzeug.wrappers import Request, Response

from .json import scriptsafe

from odoo.tools.safe_eval import _UNSAFE_ATTRIBUTES

try:
    from xlrd import xlsx
except ImportError:
    pass
else:
    from lxml import etree
    # xlrd.xlsx supports defusedxml, defusedxml's etree interface is broken
    # (missing ElementTree and thus ElementTree.iter) which causes a fallback to
    # Element.getiterator(), triggering a warning before 3.9 and an error from 3.9.
    #
    # We have defusedxml installed because zeep has a hard dep on defused and
    # doesn't want to drop it (mvantellingen/python-zeep#1014).
    #
    # Ignore the check and set the relevant flags directly using lxml as we have a
    # hard dependency on it.
    xlsx.ET = etree
    xlsx.ET_has_iterparse = True
    xlsx.Element_has_iter = True

FileStorage.save = lambda self, dst, buffer_size=1<<20: copyfileobj(self.stream, dst, buffer_size)

Request.json_module = Response.json_module = scriptsafe

get_func_code = getattr(Rule, '_get_func_code', None)
if get_func_code:
    @staticmethod
    def _get_func_code(code, name):
        assert isinstance(code, CodeType)
        return get_func_code(code, name)
    Rule._get_func_code = _get_func_code

orig_literal_eval = ast.literal_eval

def literal_eval(expr):
    # limit the size of the expression to avoid segmentation faults
    # the default limit is set to 100KiB
    # can be overridden by setting the ODOO_LIMIT_LITEVAL_BUFFER buffer_size_environment variable

    buffer_size = 102400
    buffer_size_env = os.getenv("ODOO_LIMIT_LITEVAL_BUFFER")

    if buffer_size_env:
        if buffer_size_env.isdigit():
            buffer_size = int(buffer_size_env)
        else:
            _logger.error("ODOO_LIMIT_LITEVAL_BUFFER has to be an integer, defaulting to 100KiB")

    if isinstance(expr, str) and len(expr) > buffer_size:
        raise ValueError("expression can't exceed buffer limit")

    return orig_literal_eval(expr)

ast.literal_eval = literal_eval


def _is_safe_expr(expr):
    return '__' not in expr and not any(att_name in expr for att_name in _UNSAFE_ATTRIBUTES)


origin_formatter_get_field = string.Formatter.get_field


def get_field(self, field_name, args, kwargs):
    # Monkey-patch `get_field` to raise in case of access to a forbidden name
    # Ref: https://github.com/python/cpython/blob/812245ecce2d8344c3748228047bab456816180a/Lib/string.py#L267
    if not _is_safe_expr(field_name):
        raise NameError('Access to forbidden name %r' % (field_name))
    return origin_formatter_get_field(self, field_name, args, kwargs)


string.Formatter.get_field = get_field


#
# Monkey-Patch C types
#

# PyTypeObject is not in Python ABI, so we map it to a custom ctypes Struct
class PyTypeObject(ctypes.Structure):
    # Ref: https://docs.python.org/3/c-api/typeobj.html
    _fields_ = [
        # cover PyObject variable header https://docs.python.org/3/c-api/typeobj.html#pyobject-slots
        # + 15 first PyTypeObject slots: https://docs.python.org/3/c-api/typeobj.html#pytypeobject-slots
        ('_', 18 * ctypes.c_void_p),
        # https://docs.python.org/3/c-api/typeobj.html#c.PyTypeObject.tp_getattro
        ('tp_getattro', ctypes.CFUNCTYPE(ctypes.py_object, ctypes.py_object, ctypes.py_object)),
        ('_', 14 * ctypes.c_void_p),  # cover 14 slots, not needed so far
        # https://docs.python.org/3/c-api/typeobj.html#c.PyTypeObject.tp_dict
        ('tp_dict', ctypes.py_object),
        ('_', 3 * ctypes.c_void_p),  # cover 3 slots, not needed so far
        # https://docs.python.org/3/c-api/typeobj.html#c.PyTypeObject.tp_init
        # /!\ last param mapped to c_void_p because it's nullable and PyObject doesn't support it
        ('tp_init', ctypes.CFUNCTYPE(ctypes.c_int, ctypes.py_object, ctypes.py_object, ctypes.c_void_p)),
    ]
    _slot_mapping = {
        # python_method: slot_name
        '__init__': 'tp_init',
    }


def patch_c_type(cls, attr, value):
    # obtain the address of the C type - don't assume id(cls) is guaranteed to hold it
    cls_pt = ctypes.py_object(cls)
    cls_addr = ctypes.POINTER(ctypes.c_void_p)(cls_pt)[0]
    # cast into our custom PyTypeObject struct
    obj = PyTypeObject.from_address(cls_addr)

    # CASE 1. Slot functions: replace slot function pointer
    if attr.startswith("__") and attr.endswith("__"):
        slot_func = PyTypeObject._slot_mapping[attr]
        c_func_type = dict(PyTypeObject._fields_)[slot_func]
        c_func = c_func_type(value)  # C callback pointer for our patch function

        # incref: store a ref in the type's __dict__
        cls_dict = getattr(obj, "tp_dict")
        cls_dict.setdefault('__patch_refs__', []).append(c_func)

        # apply patch function
        setattr(obj, slot_func, c_func)

    # CASE 2. Other methods: replace the method in the __dict__ of the type
    else:
        cls_dict = getattr(obj, "tp_dict")
        origin = cls_dict.get(attr)
        if origin:
            value.__name__ = origin.__name__
            value.__qualname__ = origin.__qualname__

        # apply patch function
        cls_dict[attr] = value

        # clear internal caches: https://docs.python.org/3/c-api/type.html#c.PyType_Modified
        ctypes.pythonapi.PyType_Modified(cls_pt)


# Monkey-patch AttributeError to suppress assignation of `.obj`
if hasattr(AttributeError, 'obj'):
    # AttributeError.name, AttributeError.obj added in Python 3.10
    # https://github.com/python/cpython/commit/37494b441aced0362d7edd2956ab3ea7801e60c8
    def __init__(self, args, kwargs):
        if kwargs:
            # py_object isn't NULLABLE, so we manually handle the NULL case from a void pointer
            kwargs = ctypes.cast(kwargs, ctypes.py_object).value
        else:
            kwargs = {}

        # emulate super __init__, we don't want to call it, it's cheaper
        # it's here: https://github.com/python/cpython/blob/d0524caed0f3b77f271640460d0dff1a4c784087/Objects/exceptions.c#L1404
        self.name = kwargs.get('name')

        # assign .obj immediately so set_attribute_error_context() won't do it
        # cfr https://github.com/python/cpython/commit/3b3be05a164da43f201e35b6dafbc840993a4d18
        self.obj = None  # pretend it was not really assigned (None != NULL pointer)
        return 0

    patch_c_type(AttributeError, "__init__", __init__)


def _mkpatch_str_format():
    # Monkey-patch str.format to forbid usage of dunder attributes in replacement fields,
    # keeping all refs in the closure
    formatter = string.Formatter()  # thread-safe parsing, can be shared
    origin_format = str.format
    origin_format_map = str.format_map

    def _safe_format_fields(s):
        # First quick pass with strstr(), matching both `{0.__foo__}` and `__{0}__`
        if not _is_safe_expr(s):
            # Second pass with a real parsing for "format fields" to avoid blocking `__{0}__`. cfr PEP-3101.
            field_exprs = tuple(field_expr for _lit, field_expr, _fmt, _conv in formatter.parse(s) if field_expr)
            for expr in field_exprs:
                if not _is_safe_expr(expr):
                    return False
        return True

    def format(*args, **kwargs):
        if not _safe_format_fields(args[0]):
            return args[0]  # pretend we forgot to format
        return origin_format(*args, **kwargs)

    def format_map(*args, **kwargs):
        if not _safe_format_fields(args[0]):
            return args[0]  # pretend we forgot to format
        return origin_format_map(*args, **kwargs)

    patch_c_type(str, "format", format)
    patch_c_type(str, "format_map", format_map)


_mkpatch_str_format()
