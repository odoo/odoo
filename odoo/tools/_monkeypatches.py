import ast
import os
import logging
from odoo import MIN_PY_VERSION
from shutil import copyfileobj
from types import CodeType

_logger = logging.getLogger(__name__)

try:
    import num2words
    from .num2words_patch import Num2Word_AR_Fixed
except ImportError:
    _logger.warning("num2words is not available, Arabic number to words conversion will not work")
    num2words = None

from werkzeug.datastructures import FileStorage
from werkzeug.routing import Rule
from werkzeug.wrappers import Request, Response

from .json import scriptsafe

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
    raise RuntimeError("The num2words monkey patch is obsolete. Bump the version of the library to the latest available in the official package repository, if it hasn't already been done, and remove the patch.")

if num2words:
    num2words.CONVERTER_CLASSES["ar"] = Num2Word_AR_Fixed()

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


if util:
    util.get_soap_client = new_get_soap_client
