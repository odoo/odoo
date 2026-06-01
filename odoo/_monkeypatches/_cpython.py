import ctypes
import string

from odoo.tools.safe_eval import _UNSAFE_ATTRIBUTES


#
# Monkey-Patch C types
#


class MappingProxy(ctypes.Structure):
    # https://github.com/python/cpython/blob/0691bd860d3de0c1feb1566d99315a0a582c62a0/Objects/descrobject.c#L1031-L1034
    _fields_ = [
        ('_', 2 * ctypes.c_void_p),
        ('mapping', ctypes.py_object)
    ]


def patch_c_type(cls, attr, value):
    # obtain the address of the origin dict behind the proxymapping and cast into our custom MappingProxy struct
    # Each call to cls.__dict__ returns a new temporary mappingproxy object.
    # If we don't keep a reference to it, it may be garbage-collected immediately after use (e.g., after calling id()).
    # To ensure the mapping stays alive and valid when accessed (e.g., by MappingProxy), we store it in a variable first.
    cls_dict_proxy = cls.__dict__
    cls_dict = MappingProxy.from_address(id(cls_dict_proxy)).mapping

    assert not attr.startswith("__") and not attr.endswith("__")

    # replace the method in the __dict__ of the type
    origin = cls_dict.get(attr)
    if origin:
        value.__name__ = origin.__name__
        value.__qualname__ = origin.__qualname__

    # apply patch function
    cls_dict[attr] = value

    # clear internal caches: https://docs.python.org/3/c-api/type.html#c.PyType_Modified
    ctypes.pythonapi.PyType_Modified(ctypes.py_object(cls))


def _is_safe_expr(expr):
    return '__' not in expr and not any(att_name in expr for att_name in _UNSAFE_ATTRIBUTES)


#
# String patch
#


def _patch_string_formatter_get_field():
    origin_formatter_get_field = string.Formatter.get_field

    def _patched_get_field(self, field_name, args, kwargs):
        # Monkey-patch `get_field` to raise in case of access to a forbidden name
        # Ref: https://github.com/python/cpython/blob/812245ecce2d8344c3748228047bab456816180a/Lib/string.py#L267
        if not _is_safe_expr(field_name):
            raise NameError('Access to forbidden name %r' % (field_name))
        return origin_formatter_get_field(self, field_name, args, kwargs)

    string.Formatter.get_field = _patched_get_field


def _patch_str_format():
    # keeping all refs in the closure
    formatter = string.Formatter()  # thread-safe parsing, can be shared
    origin_format = str.format
    origin_format_map = str.format_map

    def _safe_format_fields(s):
        if not _is_safe_expr(s):
            # `string.Formatter.parse` returns an iterable that contains tuples of the form:
            # (literal_text, field_name, format_spec, conversion)
            # https://github.com/python/cpython/blob/812245ecce2d8344c3748228047bab456816180a/Lib/string.py#L251-L259
            for _lit, expr, format_spec, _conv in formatter.parse(s):
                if expr and not _is_safe_expr(expr):
                    return False
                if format_spec and not _is_safe_expr(format_spec):
                    # PEP 3101 says a format expression can have 2 levels
                    # "{0:{1}}".format('abc', 's')            # works
                    # "{0:{1:{2}}}".format('abc', 's', '')    # fails
                    # https://github.com/python/cpython/blob/812245ecce2d8344c3748228047bab456816180a/Objects/stringlib/unicode_format.h#L944-L948
                    # https://github.com/python/cpython/blob/812245ecce2d8344c3748228047bab456816180a/Objects/stringlib/unicode_format.h#L914-L919
                    return False
        return True

    def format(*args, **kwargs):
        if not _safe_format_fields(args[0]):
            return args[0]
        return origin_format(*args, **kwargs)

    def format_map(*args, **kwargs):
        if not _safe_format_fields(args[0]):
            return args[0]
        return origin_format_map(*args, **kwargs)

    patch_c_type(str, "format", format)
    patch_c_type(str, "format_map", format_map)


origin_obj_member = getattr(AttributeError, 'obj', None)


def _patch_attribute_error():
    # AttributeError.name / .obj were added in Python 3.10
    # https://github.com/python/cpython/commit/37494b441aced0362d7edd2956ab3ea7801e60c8
    class EmptyMember:
        def __get__(self, obj, owner=None):
            if obj is None:
                return origin_obj_member
            return ""

        # keep original setter/deleter
        # PyCharm's pydev debugger relies on normal AttributeError handling in
        # its Cython frame-eval code, so overriding __init__ / write behavior
        # can recurse and crash the debugger with stack overflow
        # https://github.com/JetBrains/intellij-community/blob/7bc44574a8fe3a1e44425683188bd842c805fe1e/python/helpers/pydev/_pydevd_frame_eval/pydevd_frame_evaluator_39_310.pyx#L261-L266
        __set__ = origin_obj_member.__set__
        __delete__ = origin_obj_member.__delete__

    patch_c_type(AttributeError, "obj", EmptyMember())


def patch_module():
    _patch_string_formatter_get_field()
    _patch_str_format()
    _patch_attribute_error()
