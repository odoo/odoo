"""
slapdtest - module for spawning test instances of OpenLDAP's slapd server

See https://www.python-ldap.org/ for details.
"""

__version__ = '3.4.4'

from slapdtest._slapdtest import SlapdObject, SlapdTestCase, SysLogHandler
from slapdtest._slapdtest import requires_ldapi, requires_sasl, requires_tls
from slapdtest._slapdtest import requires_init_fd
from slapdtest._slapdtest import skip_unless_ci
