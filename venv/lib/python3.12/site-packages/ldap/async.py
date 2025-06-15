"""
ldap.asyncsearch - handle async LDAP search operations

See https://www.python-ldap.org/ for details.
"""
import warnings

from ldap.asyncsearch import *
from ldap.asyncsearch import __version__

warnings.warn(
    "'ldap.async module' is deprecated, import 'ldap.asyncsearch' instead.",
    DeprecationWarning,
    stacklevel=2
)
