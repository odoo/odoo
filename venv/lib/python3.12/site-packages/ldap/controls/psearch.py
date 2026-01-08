"""
ldap.controls.psearch - classes for Persistent Search Control
(see https://tools.ietf.org/html/draft-ietf-ldapext-psearch)

See https://www.python-ldap.org/ for project details.
"""

__all__ = [
  'PersistentSearchControl',
  'EntryChangeNotificationControl',
  'CHANGE_TYPES_INT',
  'CHANGE_TYPES_STR',
]

# Imports from python-ldap 2.4+
import ldap.controls
from ldap.controls import RequestControl,ResponseControl,KNOWN_RESPONSE_CONTROLS

# Imports from pyasn1
from pyasn1.type import namedtype,namedval,univ,constraint
from pyasn1.codec.ber import encoder,decoder
from pyasn1_modules.rfc2251 import LDAPDN

#---------------------------------------------------------------------------
# Constants and classes for Persistent Search Control
#---------------------------------------------------------------------------

CHANGE_TYPES_INT = {
  'add':1,
  'delete':2,
  'modify':4,
  'modDN':8,
}
CHANGE_TYPES_STR = {v: k for k,v in CHANGE_TYPES_INT.items()}


class PersistentSearchControl(RequestControl):
  """
  Implements the request control for persistent search.

  changeTypes
    List of strings specifying the types of changes returned by the server.
    Setting to None requests all changes.
  changesOnly
    Boolean which indicates whether only changes are returned by the server.
  returnECs
    Boolean which indicates whether the server should return an
    Entry Change Notification response control
  """

  class PersistentSearchControlValue(univ.Sequence):
    componentType = namedtype.NamedTypes(
      namedtype.NamedType('changeTypes',univ.Integer()),
      namedtype.NamedType('changesOnly',univ.Boolean()),
      namedtype.NamedType('returnECs',univ.Boolean()),
    )

  controlType = "2.16.840.1.113730.3.4.3"

  def __init__(self,criticality=True,changeTypes=None,changesOnly=False,returnECs=True):
    self.criticality,self.changesOnly,self.returnECs = \
      criticality,changesOnly,returnECs
    self.changeTypes = changeTypes or CHANGE_TYPES_INT.values()

  def encodeControlValue(self):
    if not type(self.changeTypes)==type(0):
      # Assume a sequence type of integers to be OR-ed
      changeTypes_int = 0
      for ct in self.changeTypes:
        changeTypes_int = changeTypes_int|CHANGE_TYPES_INT.get(ct,ct)
      self.changeTypes = changeTypes_int
    p = self.PersistentSearchControlValue()
    p.setComponentByName('changeTypes',univ.Integer(self.changeTypes))
    p.setComponentByName('changesOnly',univ.Boolean(self.changesOnly))
    p.setComponentByName('returnECs',univ.Boolean(self.returnECs))
    return encoder.encode(p)


class ChangeType(univ.Enumerated):
  namedValues = namedval.NamedValues(
    ('add',1),
    ('delete',2),
    ('modify',4),
    ('modDN',8),
  )
  subtypeSpec = univ.Enumerated.subtypeSpec + constraint.SingleValueConstraint(1,2,4,8)


class EntryChangeNotificationValue(univ.Sequence):
  componentType = namedtype.NamedTypes(
    namedtype.NamedType('changeType',ChangeType()),
    namedtype.OptionalNamedType('previousDN', LDAPDN()),
    namedtype.OptionalNamedType('changeNumber',univ.Integer()),
  )


class EntryChangeNotificationControl(ResponseControl):
  """
  Implements the response control for persistent search.

  Class attributes with values extracted from the response control:

  changeType
    String indicating the type of change causing this result to be
    returned by the server
  previousDN
    Old DN of the entry in case of a modrdn change
  changeNumber
    A change serial number returned by the server (optional).
  """

  controlType = "2.16.840.1.113730.3.4.7"

  def decodeControlValue(self,encodedControlValue):
    ecncValue,_ = decoder.decode(encodedControlValue,asn1Spec=EntryChangeNotificationValue())
    self.changeType = int(ecncValue.getComponentByName('changeType'))
    previousDN = ecncValue.getComponentByName('previousDN')
    if previousDN.hasValue():
      self.previousDN = str(previousDN)
    else:
      self.previousDN = None
    changeNumber = ecncValue.getComponentByName('changeNumber')
    if changeNumber.hasValue():
      self.changeNumber = int(changeNumber)
    else:
      self.changeNumber = None
    return (self.changeType,self.previousDN,self.changeNumber)

KNOWN_RESPONSE_CONTROLS[EntryChangeNotificationControl.controlType] = EntryChangeNotificationControl
