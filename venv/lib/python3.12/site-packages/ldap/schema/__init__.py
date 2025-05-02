"""
ldap.schema -  LDAPv3 schema handling

See https://www.python-ldap.org/ for details.
"""

from ldap import __version__

from ldap.schema.subentry import SubSchema,SCHEMA_ATTRS,SCHEMA_CLASS_MAPPING,SCHEMA_ATTR_MAPPING,urlfetch
from ldap.schema.models import *
