"""
ldap.extop.dds - Classes for Dynamic Entries extended operations
(see RFC 2589)

See https://www.python-ldap.org/ for details.
"""

from ldap.extop import ExtendedRequest,ExtendedResponse

# Imports from pyasn1
from pyasn1.type import namedtype,univ,tag
from pyasn1.codec.der import encoder,decoder
from pyasn1_modules.rfc2251 import LDAPDN


class RefreshRequest(ExtendedRequest):

  requestName = '1.3.6.1.4.1.1466.101.119.1'
  defaultRequestTtl = 86400

  class RefreshRequestValue(univ.Sequence):
    componentType = namedtype.NamedTypes(
      namedtype.NamedType(
        'entryName',
        LDAPDN().subtype(
          implicitTag=tag.Tag(tag.tagClassContext,tag.tagFormatSimple,0)
        )
      ),
      namedtype.NamedType(
        'requestTtl',
        univ.Integer().subtype(
          implicitTag=tag.Tag(tag.tagClassContext,tag.tagFormatSimple,1)
        )
      ),
    )

  def __init__(self,requestName=None,entryName=None,requestTtl=None):
    self.entryName = entryName
    self.requestTtl = requestTtl or self.defaultRequestTtl

  def encodedRequestValue(self):
    p = self.RefreshRequestValue()
    p.setComponentByName(
      'entryName',
      LDAPDN(self.entryName).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple,0)
      )
    )
    p.setComponentByName(
      'requestTtl',
      univ.Integer(self.requestTtl).subtype(
        implicitTag=tag.Tag(tag.tagClassContext,tag.tagFormatSimple,1)
      )
    )
    return encoder.encode(p)


class RefreshResponse(ExtendedResponse):
  responseName = '1.3.6.1.4.1.1466.101.119.1'

  class RefreshResponseValue(univ.Sequence):
    componentType = namedtype.NamedTypes(
      namedtype.NamedType(
        'responseTtl',
        univ.Integer().subtype(
          implicitTag=tag.Tag(tag.tagClassContext,tag.tagFormatSimple,1)
        )
      )
    )

  def decodeResponseValue(self,value):
    respValue,_ = decoder.decode(value,asn1Spec=self.RefreshResponseValue())
    self.responseTtl = int(respValue.getComponentByName('responseTtl'))
    return self.responseTtl
