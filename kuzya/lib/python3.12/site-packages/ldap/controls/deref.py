"""
ldap.controls.deref - classes for
(see https://tools.ietf.org/html/draft-masarati-ldap-deref)

See https://www.python-ldap.org/ for project details.
"""

__all__ = [
  'DEREF_CONTROL_OID',
  'DereferenceControl',
]

import ldap.controls
from ldap.controls import LDAPControl,KNOWN_RESPONSE_CONTROLS

import pyasn1_modules.rfc2251
from pyasn1.type import namedtype,univ,tag
from pyasn1.codec.ber import encoder,decoder
from pyasn1_modules.rfc2251 import LDAPDN,AttributeDescription,AttributeDescriptionList,AttributeValue


DEREF_CONTROL_OID = '1.3.6.1.4.1.4203.666.5.16'


# Request types
#---------------------------------------------------------------------------

# For compatibility with ASN.1 declaration in I-D
AttributeList = AttributeDescriptionList

class DerefSpec(univ.Sequence):
  componentType = namedtype.NamedTypes(
    namedtype.NamedType(
      'derefAttr',
      AttributeDescription()
    ),
    namedtype.NamedType(
      'attributes',
      AttributeList()
    ),
  )

class DerefSpecs(univ.SequenceOf):
  componentType = DerefSpec()

# Response types
#---------------------------------------------------------------------------


class AttributeValues(univ.SetOf):
    componentType = AttributeValue()


class PartialAttribute(univ.Sequence):
  componentType = namedtype.NamedTypes(
    namedtype.NamedType('type', AttributeDescription()),
    namedtype.NamedType('vals', AttributeValues()),
  )


class PartialAttributeList(univ.SequenceOf):
  componentType = PartialAttribute()
  tagSet = univ.Sequence.tagSet.tagImplicitly(
    tag.Tag(tag.tagClassContext,tag.tagFormatConstructed,0)
  )


class DerefRes(univ.Sequence):
  componentType = namedtype.NamedTypes(
    namedtype.NamedType('derefAttr', AttributeDescription()),
    namedtype.NamedType('derefVal', LDAPDN()),
    namedtype.OptionalNamedType('attrVals', PartialAttributeList()),
  )


class DerefResultControlValue(univ.SequenceOf):
    componentType = DerefRes()


class DereferenceControl(LDAPControl):
  controlType = DEREF_CONTROL_OID

  def __init__(self,criticality=False,derefSpecs=None):
    LDAPControl.__init__(self,self.controlType,criticality)
    self.derefSpecs = derefSpecs or {}

  def _derefSpecs(self):
    deref_specs = DerefSpecs()
    i = 0
    for deref_attr,deref_attribute_names in self.derefSpecs.items():
      deref_spec = DerefSpec()
      deref_attributes = AttributeList()
      for j in range(len(deref_attribute_names)):
        deref_attributes.setComponentByPosition(j,deref_attribute_names[j])
      deref_spec.setComponentByName('derefAttr',AttributeDescription(deref_attr))
      deref_spec.setComponentByName('attributes',deref_attributes)
      deref_specs.setComponentByPosition(i,deref_spec)
      i += 1
    return deref_specs

  def encodeControlValue(self):
    return encoder.encode(self._derefSpecs())

  def decodeControlValue(self,encodedControlValue):
    decodedValue,_ = decoder.decode(encodedControlValue,asn1Spec=DerefResultControlValue())
    self.derefRes = {}
    for deref_res in decodedValue:
      deref_attr,deref_val,deref_vals = deref_res[0],deref_res[1],deref_res[2]
      partial_attrs_dict = {
        str(tv[0]): [str(v) for v in tv[1]]
        for tv in deref_vals or []
      }
      try:
        self.derefRes[str(deref_attr)].append((str(deref_val),partial_attrs_dict))
      except KeyError:
        self.derefRes[str(deref_attr)] = [(str(deref_val),partial_attrs_dict)]

KNOWN_RESPONSE_CONTROLS[DereferenceControl.controlType] = DereferenceControl
