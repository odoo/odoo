"""
    zeep.wsdl.messages.soap
    ~~~~~~~~~~~~~~~~~~~~~~~

"""

import copy
import typing
from collections import OrderedDict

from lxml import etree
from lxml.builder import ElementMaker

from zeep import exceptions, xsd
from zeep.utils import as_qname
from zeep.wsdl.messages.base import ConcreteMessage, SerializedMessage
from zeep.wsdl.messages.multiref import process_multiref
from zeep.xsd.context import XmlParserContext
from zeep.xsd.valueobjects import CompoundValue

__all__ = ["DocumentMessage", "RpcMessage"]


class SoapMessage(ConcreteMessage):
    """Base class for the SOAP Document and RPC messages

    :param wsdl: The main wsdl document
    :type wsdl: zeep.wsdl.Document
    :param name:
    :param operation: The operation to which this message belongs
    :type operation: zeep.wsdl.bindings.soap.SoapOperation
    :param type: 'input' or 'output'
    :type type: str
    :param nsmap: The namespace mapping
    :type nsmap: dict

    """

    if typing.TYPE_CHECKING:
        _resolve_info = {}  # type: typing.Dict[str, typing.Any]

    def __init__(self, wsdl, name, operation, type, nsmap):
        super().__init__(wsdl, name, operation)
        self.nsmap = nsmap
        self.abstract = None  # Set during resolve()
        self.type = type

        self._is_body_wrapped = False
        self.body = None
        self.header = None
        self.envelope = None

    def serialize(self, *args, **kwargs):
        """Create a SerializedMessage for this message"""
        nsmap = {"soap-env": self.nsmap["soap-env"]}
        nsmap.update(self.wsdl.types._prefix_map_custom)

        soap = ElementMaker(namespace=self.nsmap["soap-env"], nsmap=nsmap)

        # Create the soap:envelope
        envelope = soap.Envelope()

        # Create the soap:header element
        headers_value = kwargs.pop("_soapheaders", None)
        header = self._serialize_header(headers_value, nsmap)
        if header is not None:
            envelope.append(header)

        # Create the soap:body element. The _is_body_wrapped attribute signals
        # that the self.body element is of type soap:body, so we don't have to
        # create it in that case. Otherwise we create a Element soap:body and
        # render the content into this.
        if self.body:
            body_value = self.body(*args, **kwargs)
            if self._is_body_wrapped:
                self.body.render(envelope, body_value)
            else:
                body = soap.Body()
                envelope.append(body)
                self.body.render(body, body_value)
        else:
            body = soap.Body()
            envelope.append(body)

        # XXX: This is only used in Soap 1.1 so should be moved to the the
        # Soap11Binding._set_http_headers(). But let's keep it like this for
        # now.
        headers = {
            "SOAPAction": (
                '"%s"' % self.operation.soapaction
                if self.operation.soapaction
                else '""'
            )
        }
        return SerializedMessage(path=None, headers=headers, content=envelope)

    def deserialize(self, envelope):
        """Deserialize the SOAP:Envelope and return a CompoundValue with the
        result.

        """
        if not self.envelope:
            return None

        assert self.header

        body = envelope.find("soap-env:Body", namespaces=self.nsmap)
        body_result = self._deserialize_body(body)

        header = envelope.find("soap-env:Header", namespaces=self.nsmap)
        headers_result = self._deserialize_headers(header)

        kwargs = body_result
        kwargs.update(headers_result)
        result = self.envelope(**kwargs)

        # If the message
        if self.header.type._element:
            return result

        result = result.body
        if not hasattr(
            result, "__len__"
        ):  # Return body directly if len is allowed (could indicated valid primitive type).
            return result
        if result is None or len(result) == 0:
            return None
        elif len(result) > 1:
            return result

        # Check if we can remove the wrapping object to make the return value
        # easier to use.
        result = next(iter(result.__values__.values()))
        if isinstance(result, xsd.CompoundValue):
            children = result._xsd_type.elements
            attributes = result._xsd_type.attributes
            if len(children) == 1 and len(attributes) == 0:
                item_name, item_element = children[0]
                retval = getattr(result, item_name)
                return retval
        return result

    def signature(self, as_output=False):
        if not self.envelope:
            return None

        if as_output:
            if isinstance(self.envelope.type, xsd.ComplexType):
                try:
                    if len(self.envelope.type.elements) == 1:
                        return self.envelope.type.elements[0][1].type.signature(
                            schema=self.wsdl.types, standalone=False
                        )
                except AttributeError:
                    return None
            return self.envelope.type.signature(
                schema=self.wsdl.types, standalone=False
            )

        if self.body:
            parts = [self.body.type.signature(schema=self.wsdl.types, standalone=False)]
        else:
            parts = []

        assert self.header
        if self.header.type._element:
            parts.append(
                "_soapheaders={%s}"
                % self.header.type.signature(schema=self.wsdl.types, standalone=False)
            )
        return ", ".join(part for part in parts if part)

    @classmethod
    def parse(cls, definitions, xmlelement, operation, type, nsmap):
        """Parse a wsdl:binding/wsdl:operation/wsdl:operation for the SOAP
        implementation.

        Each wsdl:operation can contain three child nodes:
         - input
         - output
         - fault

        Definition for input/output::

          <input>
            <soap:body parts="nmtokens"? use="literal|encoded"
                       encodingStyle="uri-list"? namespace="uri"?>

            <soap:header message="qname" part="nmtoken" use="literal|encoded"
                         encodingStyle="uri-list"? namespace="uri"?>*
              <soap:headerfault message="qname" part="nmtoken"
                                use="literal|encoded"
                                encodingStyle="uri-list"? namespace="uri"?/>*
            </soap:header>
          </input>

        And the definition for fault::

           <soap:fault name="nmtoken" use="literal|encoded"
                       encodingStyle="uri-list"? namespace="uri"?>

        """
        name = xmlelement.get("name")
        obj = cls(definitions.wsdl, name, operation, nsmap=nsmap, type=type)

        body_data = None
        header_data = None

        # After some profiling it turns out that .find() and .findall() in this
        # case are twice as fast as the xpath method
        body = xmlelement.find("soap:body", namespaces=operation.binding.nsmap)
        if body is not None:
            body_data = cls._parse_body(body)

        # Parse soap:header (multiple)
        elements = xmlelement.findall("soap:header", namespaces=operation.binding.nsmap)
        header_data = cls._parse_header(
            elements, definitions.target_namespace, operation
        )

        obj._resolve_info = {"body": body_data, "header": header_data}
        return obj

    @classmethod
    def _parse_body(cls, xmlelement):
        """Parse soap:body and return a dict with data to resolve it.

        <soap:body parts="nmtokens"? use="literal|encoded"?
                   encodingStyle="uri-list"? namespace="uri"?>

        """
        return {
            "part": xmlelement.get("part"),
            "use": xmlelement.get("use", "literal"),
            "encodingStyle": xmlelement.get("encodingStyle"),
            "namespace": xmlelement.get("namespace"),
        }

    @classmethod
    def _parse_header(cls, xmlelements, tns, operation):
        """Parse the soap:header and optionally included soap:headerfault elements

          <soap:header
            message="qname"
            part="nmtoken"
            use="literal|encoded"
            encodingStyle="uri-list"?
            namespace="uri"?
          />*

        The header can optionally contain one ore more soap:headerfault
        elements which can contain the same attributes as the soap:header::

           <soap:headerfault message="qname" part="nmtoken" use="literal|encoded"
                             encodingStyle="uri-list"? namespace="uri"?/>*

        """
        result = []
        for xmlelement in xmlelements:
            data = cls._parse_header_element(xmlelement, tns)

            # Add optional soap:headerfault elements
            data["faults"] = []
            fault_elements = xmlelement.findall(
                "soap:headerfault", namespaces=operation.binding.nsmap
            )
            for fault_element in fault_elements:
                fault_data = cls._parse_header_element(fault_element, tns)
                data["faults"].append(fault_data)

            result.append(data)
        return result

    @classmethod
    def _parse_header_element(cls, xmlelement, tns):
        attributes = xmlelement.attrib
        message_qname = as_qname(attributes["message"], xmlelement.nsmap, tns)

        try:
            return {
                "message": message_qname,
                "part": attributes["part"],
                "use": attributes["use"],
                "encodingStyle": attributes.get("encodingStyle"),
                "namespace": attributes.get("namespace"),
            }
        except KeyError:
            raise exceptions.WsdlSyntaxError("Invalid soap:header(fault)")

    def resolve(self, definitions, abstract_message):
        """Resolve the data in the self._resolve_info dict (set via parse())

        This creates three xsd.Element objects:

            - self.header
            - self.body
            - self.envelope (combination of headers and body)

        XXX headerfaults are not implemented yet.

        """
        info = self._resolve_info
        del self._resolve_info

        # If this message has no parts then we have nothing to do. This might
        # happen for output messages which don't return anything.
        if (
            abstract_message is None or not abstract_message.parts
        ) and self.type != "input":
            return

        self.abstract = abstract_message
        parts = OrderedDict(self.abstract.parts)

        self.header = self._resolve_header(info["header"], definitions, parts)
        self.body = self._resolve_body(info["body"], definitions, parts)
        self.envelope = self._create_envelope_element()

    def _create_envelope_element(self):
        """Create combined `envelope` complexType which contains both the
        elements from the body and the headers.

        """
        all_elements = xsd.Sequence([])

        assert self.header
        if self.header.type._element:
            all_elements.append(
                xsd.Element("{%s}header" % self.nsmap["soap-env"], self.header.type)
            )

        all_elements.append(
            xsd.Element(
                "{%s}body" % self.nsmap["soap-env"],
                self.body.type if self.body else None,
            )
        )

        return xsd.Element(
            "{%s}envelope" % self.nsmap["soap-env"], xsd.ComplexType(all_elements)
        )

    def _serialize_header(self, headers_value, nsmap):
        if not headers_value:
            return

        headers_value = copy.deepcopy(headers_value)

        soap = ElementMaker(namespace=self.nsmap["soap-env"], nsmap=nsmap)
        header = soap.Header()
        if isinstance(headers_value, list):
            for header_value in headers_value:
                if isinstance(header_value, CompoundValue):
                    if hasattr(header_value, "_xsd_elm"):
                        header_value._xsd_elm.render(header, header_value)
                    else:
                        header_value._xsd_type.render(header, header_value)
                elif isinstance(header_value, etree._Element):
                    header.append(header_value)
                else:
                    raise ValueError("Invalid value given to _soapheaders")
        elif isinstance(headers_value, dict):
            if not self.header:
                raise ValueError(
                    "_soapheaders only accepts a dictionary if the wsdl "
                    "defines the headers."
                )

            # Only render headers for which we have a value
            headers_value = self.header(**headers_value)
            for name, elm in self.header.type.elements:
                if name in headers_value and headers_value[name] is not None:
                    elm.render(header, headers_value[name], ["header", name])
        else:
            raise ValueError("Invalid value given to _soapheaders")

        return header

    def _deserialize_body(self, xmlelement):
        raise NotImplementedError()

    def _deserialize_headers(self, xmlelement):
        """Deserialize the values in the SOAP:Header element"""
        if not self.header or xmlelement is None:
            return {}

        context = XmlParserContext(settings=self.wsdl.settings)
        result = self.header.parse(xmlelement, self.wsdl.types, context=context)
        if result is not None:
            return {"header": result}
        return {}

    def _resolve_header(self, info, definitions, parts):
        name = etree.QName(self.nsmap["soap-env"], "Header")

        container = xsd.All(consume_other=True)
        if not info:
            return xsd.Element(name, xsd.ComplexType(container))

        for item in info:
            message_name = item["message"].text
            part_name = item["part"]

            message = definitions.get("messages", message_name)
            if message == self.abstract and part_name in parts:
                del parts[part_name]

            part = message.parts[part_name]
            if part.element:
                element = part.element.clone()
                element.attr_name = part_name
            else:
                element = xsd.Element(part_name, part.type)
            container.append(element)
        return xsd.Element(name, xsd.ComplexType(container))

    def _resolve_body(self, info, definitions, parts):
        raise NotImplementedError()


class DocumentMessage(SoapMessage):
    """In the document message there are no additional wrappers, and the
    message parts appear directly under the SOAP Body element.

    .. inheritance-diagram:: zeep.wsdl.messages.soap.DocumentMessage
       :parts: 1

    :param wsdl: The main wsdl document
    :type wsdl: zeep.wsdl.Document
    :param name:
    :param operation: The operation to which this message belongs
    :type operation: zeep.wsdl.bindings.soap.SoapOperation
    :param type: 'input' or 'output'
    :type type: str
    :param nsmap: The namespace mapping
    :type nsmap: dict


    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _deserialize_body(self, xmlelement):

        if not self._is_body_wrapped:
            # TODO: For now we assume that the body only has one child since
            # only one part is specified in the wsdl. This should be handled
            # way better
            xmlelement = list(xmlelement)[0]

        context = XmlParserContext(settings=self.wsdl.settings)
        result = self.body.parse(xmlelement, self.wsdl.types, context=context)
        return {"body": result}

    def _resolve_body(self, info, definitions, parts):
        name = etree.QName(self.nsmap["soap-env"], "Body")

        if not info or not parts:
            return None

        # If the part name is omitted then all parts are available under
        # the soap:body tag. Otherwise only the part with the given name.
        if info["part"]:
            part_name = info["part"]
            sub_elements = [parts[part_name].element]
        else:
            sub_elements = []
            for part_name, part in parts.items():
                if part.element is not None:
                    element = part.element.clone()
                    element.attr_name = part_name or element.name
                else:
                    element = xsd.Element(name=part_name, type_=part.type)
                sub_elements.append(element)

        if len(sub_elements) > 1:
            self._is_body_wrapped = True
            return xsd.Element(name, xsd.ComplexType(xsd.All(sub_elements)))
        else:
            self._is_body_wrapped = False
            return sub_elements[0]


class RpcMessage(SoapMessage):
    """In RPC messages each part is a parameter or a return value and appears
    inside a wrapper element within the body.

    The wrapper element is named identically to the operation name and its
    namespace is the value of the namespace attribute.  Each message part
    (parameter) appears under the wrapper, represented by an accessor named
    identically to the corresponding parameter of the call.  Parts are arranged
    in the same order as the parameters of the call.

    .. inheritance-diagram:: zeep.wsdl.messages.soap.DocumentMessage
       :parts: 1


    :param wsdl: The main wsdl document
    :type wsdl: zeep.wsdl.Document
    :param name:
    :param operation: The operation to which this message belongs
    :type operation: zeep.wsdl.bindings.soap.SoapOperation
    :param type: 'input' or 'output'
    :type type: str
    :param nsmap: The namespace mapping
    :type nsmap: dict

    """

    def _resolve_body(self, info, definitions, parts):
        """Return an XSD element for the SOAP:Body.

        Each part is a parameter or a return value and appears inside a
        wrapper element within the body named identically to the operation
        name and its namespace is the value of the namespace attribute.

        """
        if not info:
            return None

        namespace = info["namespace"]
        if self.type == "input":
            tag_name = etree.QName(namespace, self.operation.name)
        else:
            tag_name = etree.QName(namespace, self.abstract.name.localname)

        # Create the xsd element to create/parse the response. Each part
        # is a sub element of the root node (which uses the operation name)
        elements = []
        for name, msg in parts.items():
            if msg.element:
                elements.append(msg.element)
            else:
                elements.append(xsd.Element(name, msg.type))
        return xsd.Element(tag_name, xsd.ComplexType(xsd.Sequence(elements)))

    def _deserialize_body(self, body_element):
        """The name of the wrapper element is not defined. The WS-I defines
        that it should be the operation name with the 'Response' string as
        suffix. But lets just do it really stupid for now and use the first
        element.

        """
        process_multiref(body_element)

        response_element = list(body_element)[0]
        if self.body:
            context = XmlParserContext(self.wsdl.settings)
            result = self.body.parse(response_element, self.wsdl.types, context=context)
            return {"body": result}
        return {"body": None}
