"""
ldap.controls.readentry - classes for the Read Entry controls
(see RFC 4527)

See https://www.python-ldap.org/ for project details.
"""

import ldap

from pyasn1.codec.ber import encoder,decoder
from ldap.controls import LDAPControl,KNOWN_RESPONSE_CONTROLS

from pyasn1_modules.rfc2251 import AttributeDescriptionList,SearchResultEntry


class ReadEntryControl(LDAPControl):
  """
  Base class for read entry control described in RFC 4527

  attrList
      list of attribute type names requested

  Class attributes with values extracted from the response control:

  dn
      string holding the distinguished name of the LDAP entry
  entry
      dictionary holding the LDAP entry
  """

  def __init__(self,criticality=False,attrList=None):
    self.criticality,self.attrList,self.entry = criticality,attrList or [],None

  def encodeControlValue(self):
    attributeSelection = AttributeDescriptionList()
    for i in range(len(self.attrList)):
      attributeSelection.setComponentByPosition(i,self.attrList[i])
    return encoder.encode(attributeSelection)

  def decodeControlValue(self,encodedControlValue):
    decodedEntry,_ = decoder.decode(encodedControlValue,asn1Spec=SearchResultEntry())
    self.dn = str(decodedEntry[0])
    self.entry = {}
    for attr in decodedEntry[1]:
      self.entry[str(attr[0])] = [ bytes(attr_value) for attr_value in attr[1] ]


class PreReadControl(ReadEntryControl):
  """
  Class for pre-read control described in RFC 4527

  attrList
      list of attribute type names requested

  Class attributes with values extracted from the response control:

  dn
      string holding the distinguished name of the LDAP entry
      before the operation was done by the server
  entry
      dictionary holding the LDAP entry
      before the operation was done by the server
  """
  controlType = ldap.CONTROL_PRE_READ

KNOWN_RESPONSE_CONTROLS[PreReadControl.controlType] = PreReadControl


class PostReadControl(ReadEntryControl):
  """
  Class for post-read control described in RFC 4527

  attrList
      list of attribute type names requested

  Class attributes with values extracted from the response control:

  dn
      string holding the distinguished name of the LDAP entry
      after the operation was done by the server
  entry
      dictionary holding the LDAP entry
      after the operation was done by the server
  """
  controlType = ldap.CONTROL_POST_READ

KNOWN_RESPONSE_CONTROLS[PostReadControl.controlType] = PostReadControl
