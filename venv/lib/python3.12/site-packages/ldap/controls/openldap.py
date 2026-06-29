"""
ldap.controls.openldap - classes for OpenLDAP-specific controls

See https://www.python-ldap.org/ for project details.
"""

import ldap.controls
from ldap.controls import ValueLessRequestControl,ResponseControl

from pyasn1.type import univ
from pyasn1.codec.ber import decoder


__all__ = [
  'SearchNoOpControl',
  'SearchNoOpMixIn',
]


class SearchNoOpControl(ValueLessRequestControl,ResponseControl):
  """
  No-op control attached to search operations implementing sort of a
  count operation

  see https://www.openldap.org/its/index.cgi?findid=6598
  """
  controlType = '1.3.6.1.4.1.4203.666.5.18'

  def __init__(self,criticality=False):
    self.criticality = criticality

  class SearchNoOpControlValue(univ.Sequence):
    pass

  def decodeControlValue(self,encodedControlValue):
    decodedValue,_ = decoder.decode(encodedControlValue,asn1Spec=self.SearchNoOpControlValue())
    self.resultCode = int(decodedValue[0])
    self.numSearchResults = int(decodedValue[1])
    self.numSearchContinuations = int(decodedValue[2])


ldap.controls.KNOWN_RESPONSE_CONTROLS[SearchNoOpControl.controlType] = SearchNoOpControl


class SearchNoOpMixIn:
  """
  Mix-in class to be used with class LDAPObject and friends.

  It adds a convenience method noop_search_st() to LDAPObject
  for easily using the no-op search control.
  """

  def noop_search_st(self,base,scope=ldap.SCOPE_SUBTREE,filterstr='(objectClass=*)',timeout=-1):
    try:
      msg_id = self.search_ext(
        base,
        scope,
        filterstr=filterstr,
        attrlist=['1.1'],
        timeout=timeout,
        serverctrls=[SearchNoOpControl(criticality=True)],
      )
      _,_,_,search_response_ctrls = self.result3(msg_id,all=1,timeout=timeout)
    except (
      ldap.TIMEOUT,
      ldap.TIMELIMIT_EXCEEDED,
      ldap.SIZELIMIT_EXCEEDED,
      ldap.ADMINLIMIT_EXCEEDED
    ) as e:
      self.abandon(msg_id)
      raise e
    else:
      noop_srch_ctrl = [
        c
        for c in search_response_ctrls
        if c.controlType==SearchNoOpControl.controlType
      ]
      if noop_srch_ctrl:
        return noop_srch_ctrl[0].numSearchResults,noop_srch_ctrl[0].numSearchContinuations
      else:
        return (None,None)
