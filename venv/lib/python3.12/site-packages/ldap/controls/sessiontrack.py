"""
ldap.controls.sessiontrack - class for session tracking control
(see draft-wahl-ldap-session)

See https://www.python-ldap.org/ for project details.
"""

from ldap.controls import RequestControl

from pyasn1.type import namedtype,univ
from pyasn1.codec.ber import encoder
from pyasn1_modules.rfc2251 import LDAPString,LDAPOID


# OID constants
SESSION_TRACKING_CONTROL_OID = "1.3.6.1.4.1.21008.108.63.1"
SESSION_TRACKING_FORMAT_OID_RADIUS_ACCT_SESSION_ID = SESSION_TRACKING_CONTROL_OID+".1"
SESSION_TRACKING_FORMAT_OID_RADIUS_ACCT_MULTI_SESSION_ID = SESSION_TRACKING_CONTROL_OID+".2"
SESSION_TRACKING_FORMAT_OID_USERNAME = SESSION_TRACKING_CONTROL_OID+".3"


class SessionTrackingControl(RequestControl):
  """
  Class for Session Tracking Control

  Because criticality MUST be false for this control it cannot be set
  from the application.

  sessionSourceIp
    IP address of the request source as string
  sessionSourceName
    Name of the request source as string
  formatOID
    OID as string specifying the format
  sessionTrackingIdentifier
    String containing a specific tracking ID
  """

  class SessionIdentifierControlValue(univ.Sequence):
    componentType = namedtype.NamedTypes(
      namedtype.NamedType('sessionSourceIp',LDAPString()),
      namedtype.NamedType('sessionSourceName',LDAPString()),
      namedtype.NamedType('formatOID',LDAPOID()),
      namedtype.NamedType('sessionTrackingIdentifier',LDAPString()),
    )

  controlType = SESSION_TRACKING_CONTROL_OID

  def __init__(self,sessionSourceIp,sessionSourceName,formatOID,sessionTrackingIdentifier):
    # criticality MUST be false for this control
    self.criticality = False
    self.sessionSourceIp,self.sessionSourceName,self.formatOID,self.sessionTrackingIdentifier = \
      sessionSourceIp,sessionSourceName,formatOID,sessionTrackingIdentifier

  def encodeControlValue(self):
    s = self.SessionIdentifierControlValue()
    s.setComponentByName('sessionSourceIp',LDAPString(self.sessionSourceIp))
    s.setComponentByName('sessionSourceName',LDAPString(self.sessionSourceName))
    s.setComponentByName('formatOID',LDAPOID(self.formatOID))
    s.setComponentByName('sessionTrackingIdentifier',LDAPString(self.sessionTrackingIdentifier))
    return encoder.encode(s)
