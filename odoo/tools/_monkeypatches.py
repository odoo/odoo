import ast
import ctypes
import os
import re
import logging
import requests
import json
import string
from email._policybase import _PolicyBase
from odoo import MIN_PY_VERSION
from odoo.tools.parse_version import parse_version
from shutil import copyfileobj
from types import CodeType
from importlib.metadata import version
from markupsafe import Markup

_logger = logging.getLogger(__name__)

try:
    import num2words
    from .num2words_patch import Num2Word_AR_Fixed
except ImportError:
    _logger.warning("num2words is not available, Arabic number to words conversion will not work")
    num2words = None

from urllib3 import PoolManager
from werkzeug.datastructures import FileStorage, MultiDict
from werkzeug.routing import Rule
from werkzeug.wrappers import Request, Response

from .json import scriptsafe
from .safe_eval import _UNSAFE_ATTRIBUTES  # noqa: E402

try:
    from stdnum import util
except ImportError:
    util = None

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


def _multidict_deepcopy(self, memo=None):
    return orig_deepcopy(self)


orig_deepcopy = MultiDict.deepcopy
MultiDict.deepcopy = _multidict_deepcopy

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

if MIN_PY_VERSION >= (3, 12):
    raise RuntimeError("The num2words monkey patch for Arabic is obsolete. Bump the version of the library to the latest available in the official package repository, if it hasn't already been done, and remove the patch.")
if MIN_PY_VERSION >= (3, 13):
    raise RuntimeError("The num2words monkey patch for Czech is obsolete. Bump the version of the library to the latest available in the official package repository, if it hasn't already been done, and remove the patch.")

if num2words:
    num2words.CONVERTER_CLASSES["ar"] = Num2Word_AR_Fixed()
    if 'cz' in num2words.CONVERTER_CLASSES and not 'cs' in num2words.CONVERTER_CLASSES:
        # There is a mistake in the Czech language code in versions < 0.5.14. Map it to the correct code here.
        num2words.CONVERTER_CLASSES['cs'] = num2words.CONVERTER_CLASSES['cz']

_soap_clients = {}


def new_get_soap_client(wsdlurl, timeout=30):
    # stdnum library does not set the timeout for the zeep Transport class correctly
    # (timeout is to fetch the wsdl and operation_timeout is to perform the call),
    # requiring us to monkey patch the get_soap_client function.
    # Can be removed when https://github.com/arthurdejong/python-stdnum/issues/444 is
    # resolved and the version of the dependency is updated.
    # The code is a copy of the original apart for the line related to the Transport class.
    # This was done to keep the code as similar to the original and to reduce the possibility
    # of introducing import errors, even though some imports are not in the requirements.
    # See https://github.com/odoo/odoo/pull/173359 for a more thorough explanation.
    if (wsdlurl, timeout) not in _soap_clients:
        try:
            from zeep.transports import Transport
            transport = Transport(operation_timeout=timeout, timeout=timeout)  # operational_timeout added here
            from zeep import CachingClient
            client = CachingClient(wsdlurl, transport=transport).service
        except ImportError:
            # fall back to non-caching zeep client
            try:
                from zeep import Client
                client = Client(wsdlurl, transport=transport).service
            except ImportError:
                # other implementations require passing the proxy config
                try:
                    from urllib import getproxies
                except ImportError:
                    from urllib.request import getproxies
                # fall back to suds
                try:
                    from suds.client import Client
                    client = Client(
                        wsdlurl, proxy=getproxies(), timeout=timeout).service
                except ImportError:
                    # use pysimplesoap as last resort
                    try:
                        from pysimplesoap.client import SoapClient
                        client = SoapClient(
                            wsdl=wsdlurl, proxy=getproxies(), timeout=timeout)
                    except ImportError:
                        raise ImportError(
                            'No SOAP library (such as zeep) found')
        _soap_clients[(wsdlurl, timeout)] = client
    return _soap_clients[(wsdlurl, timeout)]


if util and parse_version(version("python-stdnum")) < parse_version("2.0"):
    util.get_soap_client = new_get_soap_client


def pool_init(self, *args, **kwargs):
    orig_pool_init(self, *args, **kwargs)
    self.pool_classes_by_scheme = {**self.pool_classes_by_scheme}


orig_pool_init = PoolManager.__init__
PoolManager.__init__ = pool_init


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


# AttributeError.name / .obj were added in Python 3.10
# https://github.com/python/cpython/commit/37494b441aced0362d7edd2956ab3ea7801e60c8
if hasattr(AttributeError, 'obj'):
    origin_obj_member = AttributeError.obj

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


def _mkpatch_str_format():
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


_mkpatch_str_format()


def policy_clone(self, **kwargs):
    for arg in kwargs:
        if arg.startswith("_") or "__" in arg or arg == "clone":
            raise AttributeError(f"{self.__class__.__name__!r} object has no attribute {arg!r}")
    return orig_policy_clone(self, **kwargs)


def policy_add(self, other):
    return policy_clone(self, **other.__dict__)


orig_policy_clone = _PolicyBase.clone
_PolicyBase.clone = policy_clone
_PolicyBase.__add__ = policy_add

orig_request_json = requests.Response.json

# The requests library uses different libraries to parse json objects depending on
# whether or not the simplejson library is installed
# (https://github.com/psf/requests/blob/dc9dbdfb3434c6e58d48fd102f93e5342308817e/src/requests/compat.py#L74).
# This in turn causes our try/excepts to fail if the simplejson library is installed in the env
# we simply re-raise the json error in case the simplejson library is installed so our try/excepts flows
# are not broken by the existence of a random package
# This is only valid for python versions < 3.10 that install requests==2.25.  This issue
# was fixed in requests==2.27

try:
    import simplejson
except ImportError:
    pass    # no need to change anything if simplejson isn't installed
else:
    def new_json(self, **kwargs):
        try:
            return orig_request_json(self, **kwargs)
        except simplejson.JSONDecodeError as e:
            raise json.JSONDecodeError(e.msg, e.doc, e.pos)
    requests.Response.json = new_json

orig_markupsafe_striptags = Markup.striptags
# No need for patching in older versions
if parse_version(version("markupsafe")) >= parse_version("2.1.4"):
    MARKUPSAFE_STRIP_COMMENTS_RE = re.compile(r"<!--.*?-->", re.DOTALL)
    MARKUPSAFE_STRIP_TAGS_RE = re.compile(r"<.*?>", re.DOTALL)

    def striptags(self) -> str:
        """
        ---------------------------------------------------------
        MarkupSafe changed the implementation of striptags starting
        version 2.1.4, which is causing a significant performance
        regression for large inputs.
        The following patch reverts the striptags implementation to
        the one from version 2.1.3, which is more efficient for large
        inputs.
        ---------------------------------------------------------
        :meth:`unescape` the markup, remove tags, and normalize
        whitespace to single spaces.

        >>> Markup("Main &raquo;\t<em>About</em>").striptags()
        'Main » About'
        """
        # Use two regexes to avoid ambiguous matches.
        value = MARKUPSAFE_STRIP_COMMENTS_RE.sub("", self)  # noqa: RUF052
        value = MARKUPSAFE_STRIP_TAGS_RE.sub("", value)  # noqa: RUF052
        value = " ".join(value.split())
        return self.__class__(value).unescape()

    Markup.striptags = striptags
