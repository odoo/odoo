"""Compatibility wrappers for Py2/Py3."""
import warnings

warnings.warn(
    "The ldap.compat module is deprecated and will be removed in the future",
    DeprecationWarning,
)

from collections import UserDict
IterableUserDict = UserDict
from urllib.parse import quote, quote_plus, unquote, urlparse
from urllib.request import urlopen
from collections.abc import MutableMapping
from shutil import which

def reraise(exc_type, exc_value, exc_traceback):
    """Re-raise an exception given information from sys.exc_info()

    Note that unlike six.reraise, this does not support replacing the
    traceback. All arguments must come from a single sys.exc_info() call.
    """
    # In Python 3, all exception info is contained in one object.
    raise exc_value
