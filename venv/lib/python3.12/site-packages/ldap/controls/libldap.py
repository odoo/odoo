"""
controls.libldap - LDAP controls wrapper classes with en-/decoding done
by OpenLDAP functions

See https://www.python-ldap.org/ for details.
"""

from ldap.pkginfo import __version__

import _ldap
assert _ldap.__version__==__version__, \
       ImportError(f'ldap {__version__} and _ldap {_ldap.__version__} version mismatch!')

import ldap

from ldap.controls import RequestControl,LDAPControl,KNOWN_RESPONSE_CONTROLS


class AssertionControl(RequestControl):
  """
  LDAP Assertion control, as defined in RFC 4528

  filterstr
    LDAP filter string specifying which assertions have to match
    so that the server processes the operation
  """

  controlType = ldap.CONTROL_ASSERT
  def __init__(self,criticality=True,filterstr='(objectClass=*)'):
    self.criticality = criticality
    self.filterstr = filterstr

  def encodeControlValue(self):
    return _ldap.encode_assertion_control(self.filterstr)

KNOWN_RESPONSE_CONTROLS[ldap.CONTROL_ASSERT] = AssertionControl


class MatchedValuesControl(RequestControl):
  """
  LDAP Matched Values control, as defined in RFC 3876

  filterstr
    LDAP filter string specifying which attribute values
    should be returned
  """

  controlType = ldap.CONTROL_VALUESRETURNFILTER

  def __init__(self,criticality=False,filterstr='(objectClass=*)'):
    self.criticality = criticality
    self.filterstr = filterstr

  def encodeControlValue(self):
    return _ldap.encode_valuesreturnfilter_control(self.filterstr)

KNOWN_RESPONSE_CONTROLS[ldap.CONTROL_VALUESRETURNFILTER] = MatchedValuesControl


class SimplePagedResultsControl(LDAPControl):
  """
  LDAP Control Extension for Simple Paged Results Manipulation

  size
    Page size requested (number of entries to be returned)
  cookie
    Cookie string received with last page
  """
  controlType = ldap.CONTROL_PAGEDRESULTS

  def __init__(self,criticality=False,size=None,cookie=None):
    self.criticality = criticality
    self.size,self.cookie = size,cookie

  def encodeControlValue(self):
    return _ldap.encode_page_control(self.size,self.cookie)

  def decodeControlValue(self,encodedControlValue):
    self.size,self.cookie = _ldap.decode_page_control(encodedControlValue)

KNOWN_RESPONSE_CONTROLS[ldap.CONTROL_PAGEDRESULTS] = SimplePagedResultsControl
