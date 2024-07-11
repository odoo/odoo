import ast
import os
import logging
from shutil import copyfileobj
from types import CodeType

_logger = logging.getLogger(__name__)

try:
    from stdnum import util
except ImportError as e:
    util = None
    _logger.warning("Failed to import stdnum library: %s", e)

from werkzeug.datastructures import FileStorage
from werkzeug.routing import Rule
from werkzeug.wrappers import Request, Response

try:
    from zeep import CachingClient
    from zeep.transports import Transport
except ImportError as e:
    CachingClient = None
    Transport = None
    _logger.warning("Failed to import zeep library: %s", e)

from .json import scriptsafe

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

_soap_clients = {}

def new_get_soap_client(wsdlurl, timeout=30):
    # stdnum library does not set the timeout for the zeep Transport class correctly
    # (timeout is is to fetch the wsdl and operation_timeout is to perform the call),
    # requiring us to monkey patch the get_soap_client function.
    # Can be removed when https://github.com/arthurdejong/python-stdnum/issues/444 is
    # resolved and the version of the dependency is updated
    if (wsdlurl, timeout) not in _soap_clients:
        if Transport:
            transport = Transport(operation_timeout=timeout, timeout=timeout)
        if CachingClient:
            client = CachingClient(wsdlurl, transport=transport).service
        _soap_clients[(wsdlurl, timeout)] = client
    return _soap_clients[(wsdlurl, timeout)]


if util:
    util.get_soap_client = new_get_soap_client
