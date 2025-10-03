"""
ldap.controls.simple - classes for some very simple LDAP controls

See https://www.python-ldap.org/ for details.
"""

import struct,ldap
from ldap.controls import RequestControl,ResponseControl,LDAPControl,KNOWN_RESPONSE_CONTROLS

from pyasn1.type import univ
from pyasn1.codec.ber import encoder,decoder


class ValueLessRequestControl(RequestControl):
  """
  Base class for controls without a controlValue.
  The presence of the control in a LDAPv3 request changes the server's
  behaviour when processing the request simply based on the controlType.

  controlType
    OID of the request control
  criticality
    criticality request control
  """

  def __init__(self,controlType=None,criticality=False):
    self.controlType = controlType
    self.criticality = criticality

  def encodeControlValue(self):
    return None


class OctetStringInteger(LDAPControl):
  """
  Base class with controlValue being unsigend integer values

  integerValue
    Integer to be sent as OctetString
  """

  def __init__(self,controlType=None,criticality=False,integerValue=None):
    self.controlType = controlType
    self.criticality = criticality
    self.integerValue = integerValue

  def encodeControlValue(self):
    return struct.pack('!Q',self.integerValue)

  def decodeControlValue(self,encodedControlValue):
    self.integerValue = struct.unpack('!Q',encodedControlValue)[0]


class BooleanControl(LDAPControl):
  """
  Base class for simple request controls with boolean control value.

  Constructor argument and class attribute:

  booleanValue
    Boolean (True/False or 1/0) which is the boolean controlValue.
  """

  def __init__(self,controlType=None,criticality=False,booleanValue=False):
    self.controlType = controlType
    self.criticality = criticality
    self.booleanValue = booleanValue

  def encodeControlValue(self):
    return encoder.encode(self.booleanValue,asn1Spec=univ.Boolean())

  def decodeControlValue(self,encodedControlValue):
    decodedValue,_ = decoder.decode(encodedControlValue,asn1Spec=univ.Boolean())
    self.booleanValue = bool(int(decodedValue))


class ManageDSAITControl(ValueLessRequestControl):
  """
  Manage DSA IT Control
  """

  def __init__(self,criticality=False):
    ValueLessRequestControl.__init__(self,ldap.CONTROL_MANAGEDSAIT,criticality=False)

KNOWN_RESPONSE_CONTROLS[ldap.CONTROL_MANAGEDSAIT] = ManageDSAITControl


class RelaxRulesControl(ValueLessRequestControl):
  """
  Relax Rules Control
  """

  def __init__(self,criticality=False):
    ValueLessRequestControl.__init__(self,ldap.CONTROL_RELAX,criticality=False)

KNOWN_RESPONSE_CONTROLS[ldap.CONTROL_RELAX] = RelaxRulesControl


class ProxyAuthzControl(RequestControl):
  """
  Proxy Authorization Control

  authzId
    string containing the authorization ID indicating the identity
    on behalf which the server should process the request
  """

  def __init__(self,criticality,authzId):
    RequestControl.__init__(self,ldap.CONTROL_PROXY_AUTHZ,criticality,authzId)


class AuthorizationIdentityRequestControl(ValueLessRequestControl):
  """
  Authorization Identity Request and Response Controls
  """
  controlType = '2.16.840.1.113730.3.4.16'

  def __init__(self,criticality):
    ValueLessRequestControl.__init__(self,self.controlType,criticality)


class AuthorizationIdentityResponseControl(ResponseControl):
  """
  Authorization Identity Request and Response Controls

  Class attributes:

  authzId
    decoded authorization identity
  """
  controlType = '2.16.840.1.113730.3.4.15'

  def decodeControlValue(self,encodedControlValue):
    self.authzId = encodedControlValue


KNOWN_RESPONSE_CONTROLS[AuthorizationIdentityResponseControl.controlType] = AuthorizationIdentityResponseControl


class GetEffectiveRightsControl(RequestControl):
  """
  Get Effective Rights Control
  """

  def __init__(self,criticality,authzId=None):
    RequestControl.__init__(self,'1.3.6.1.4.1.42.2.27.9.5.2',criticality,authzId)
