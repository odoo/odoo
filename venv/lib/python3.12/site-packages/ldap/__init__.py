"""
ldap - base module

See https://www.python-ldap.org/ for details.
"""

# This is also the overall release version number

from ldap.pkginfo import __version__, __author__, __license__

import os
import sys

if __debug__:
  # Tracing is only supported in debugging mode
  import atexit
  import traceback
  _trace_level = int(os.environ.get("PYTHON_LDAP_TRACE_LEVEL", 0))
  _trace_file = os.environ.get("PYTHON_LDAP_TRACE_FILE")
  if _trace_file is None:
    _trace_file = sys.stderr
  else:
    _trace_file = open(_trace_file, 'a')
    atexit.register(_trace_file.close)
  _trace_stack_limit = None
else:
  # Any use of the _trace attributes should be guarded by `if __debug__`,
  # so they should not be needed here.
  # But, providing different API for debug mode is unnecessarily fragile.
  _trace_level = 0
  _trace_file = sys.stderr
  _trace_stack_limit = None

import _ldap
assert _ldap.__version__==__version__, \
       ImportError(f'ldap {__version__} and _ldap {_ldap.__version__} version mismatch!')
from _ldap import *
# call into libldap to initialize it right now
LIBLDAP_API_INFO = _ldap.get_option(_ldap.OPT_API_INFO)

OPT_NAMES_DICT = {}
for k,v in vars(_ldap).items():
  if k.startswith('OPT_'):
    OPT_NAMES_DICT[v]=k

class DummyLock:
  """Define dummy class with methods compatible to threading.Lock"""
  def __init__(self):
    pass
  def acquire(self):
    pass
  def release(self):
    pass

try:
  # Check if Python installation was build with thread support
  import threading
except ImportError:
  LDAPLockBaseClass = DummyLock
else:
  LDAPLockBaseClass = threading.Lock


class LDAPLock:
  """
  Mainly a wrapper class to log all locking events.
  Note that this cumbersome approach with _lock attribute was taken
  since threading.Lock is not suitable for sub-classing.
  """
  _min_trace_level = 3

  def __init__(self,lock_class=None,desc=''):
    """
    lock_class
        Class compatible to threading.Lock
    desc
        Description shown in debug log messages
    """
    self._desc = desc
    self._lock = (lock_class or LDAPLockBaseClass)()

  def acquire(self):
    if __debug__:
      global _trace_level
      if _trace_level>=self._min_trace_level:
        _trace_file.write('***{}.acquire() {} {}\n'.format(self.__class__.__name__,repr(self),self._desc))
    return self._lock.acquire()

  def release(self):
    if __debug__:
      global _trace_level
      if _trace_level>=self._min_trace_level:
        _trace_file.write('***{}.release() {} {}\n'.format(self.__class__.__name__,repr(self),self._desc))
    return self._lock.release()


# Create module-wide lock for serializing all calls into underlying LDAP lib
_ldap_module_lock = LDAPLock(desc='Module wide')

from ldap.functions import initialize,get_option,set_option,escape_str,strf_secs,strp_secs

from ldap.ldapobject import NO_UNIQUE_ENTRY, LDAPBytesWarning

from ldap.dn import explode_dn,explode_rdn,str2dn,dn2str
del str2dn
del dn2str

# More constants

# For compatibility of 2.3 and 2.4 OpenLDAP API
OPT_DIAGNOSTIC_MESSAGE = OPT_ERROR_STRING
