"""
    zeep.wsdl.messages.mime
    ~~~~~~~~~~~~~~~~~~~~~~~

"""
from urllib.parse import urlencode

from lxml import etree
from lxml.etree import fromstring

from zeep import ns, xsd
from zeep.helpers import serialize_object
from zeep.wsdl.messages.base import ConcreteMessage, SerializedMessage
from zeep.wsdl.utils import etree_to_string

__all__ = ["MimeContent", "MimeXML", "MimeMultipart"]


class MimeMessage(ConcreteMessage):
    _nsmap = {"mime": ns.MIME}

    def __init__(self, wsdl, name, operation, part_name):
        super().__init__(wsdl, name, operation)
        self.part_name = part_name

    def resolve(self, definitions, abstract_message):
        """Resolve the body element

        The specs are (again) not really clear how to handle the message
        parts in relation the message element vs type. The following strategy
        is chosen, which seem to work:

         - If the message part has a name and it maches then set it as body
         - If the message part has a name but it doesn't match but there are no
           other message parts, then just use that one.
         - If the message part has no name then handle it like an rpc call,
           in other words, each part is an argument.

        """
        self.abstract = abstract_message
        if self.part_name and self.abstract.parts:
            if self.part_name in self.abstract.parts:
                message = self.abstract.parts[self.part_name]
            elif len(self.abstract.parts) == 1:
                message = list(self.abstract.parts.values())[0]
            else:
                raise ValueError(
                    "Multiple parts for message %r while no matching part found"
                    % self.part_name
                )

            if message.element:
                self.body = message.element
            else:
                elm = xsd.Element(self.part_name, message.type)
                self.body = xsd.Element(
                    self.operation.name, xsd.ComplexType(xsd.Sequence([elm]))
                )
        else:
            children = []
            for name, message in self.abstract.parts.items():
                if message.element:
                    elm = message.element.clone(name)
                else:
                    elm = xsd.Element(name, message.type)
                children.append(elm)
            self.body = xsd.Element(
                self.operation.name, xsd.ComplexType(xsd.Sequence(children))
            )


class MimeContent(MimeMessage):
    """WSDL includes a way to bind abstract types to concrete messages in some
    MIME format.

    Bindings for the following MIME types are defined:

    - multipart/related
    - text/xml
    - application/x-www-form-urlencoded
    - Others (by specifying the MIME type string)

    The set of defined MIME types is both large and evolving, so it is not a
    goal for WSDL to exhaustively define XML grammar for each MIME type.

    :param wsdl: The main wsdl document
    :type wsdl: zeep.wsdl.wsdl.Document
    :param name:
    :param operation: The operation to which this message belongs
    :type operation: zeep.wsdl.bindings.soap.SoapOperation
    :param part_name:
    :type type: str

    """

    def __init__(self, wsdl, name, operation, content_type, part_name):
        super().__init__(wsdl, name, operation, part_name)
        self.content_type = content_type

    def serialize(self, *args, **kwargs):
        value = self.body(*args, **kwargs)
        headers = {"Content-Type": self.content_type}

        data = ""
        if self.content_type == "application/x-www-form-urlencoded":
            items = serialize_object(value)
            data = urlencode(items)
        elif self.content_type == "text/xml":
            document = etree.Element("root")
            self.body.render(document, value)
            data = etree_to_string(list(document)[0])

        return SerializedMessage(
            path=self.operation.location, headers=headers, content=data
        )

    def deserialize(self, node):
        node = fromstring(node)
        part = list(self.abstract.parts.values())[0]
        return part.type.parse_xmlelement(node)

    @classmethod
    def parse(cls, definitions, xmlelement, operation):
        name = xmlelement.get("name")

        part_name = content_type = None
        content_node = xmlelement.find("mime:content", namespaces=cls._nsmap)
        if content_node is not None:
            content_type = content_node.get("type")
            part_name = content_node.get("part")

        obj = cls(definitions.wsdl, name, operation, content_type, part_name)
        return obj


class MimeXML(MimeMessage):
    """To specify XML payloads that are not SOAP compliant (do not have a SOAP
    Envelope), but do have a particular schema, the mime:mimeXml element may be
    used to specify that concrete schema.

    The part attribute refers to a message part defining the concrete schema of
    the root XML element. The part attribute MAY be omitted if the message has
    only a single part. The part references a concrete schema using the element
    attribute for simple parts or type attribute for composite parts

    :param wsdl: The main wsdl document
    :type wsdl: zeep.wsdl.wsdl.Document
    :param name:
    :param operation: The operation to which this message belongs
    :type operation: zeep.wsdl.bindings.soap.SoapOperation
    :param part_name:
    :type type: str

    """

    def serialize(self, *args, **kwargs):
        raise NotImplementedError()

    def deserialize(self, node):
        node = fromstring(node)
        part = next(iter(self.abstract.parts.values()), None)
        return part.element.parse(node, self.wsdl.types)

    @classmethod
    def parse(cls, definitions, xmlelement, operation):
        name = xmlelement.get("name")
        part_name = None

        content_node = xmlelement.find("mime:mimeXml", namespaces=cls._nsmap)
        if content_node is not None:
            part_name = content_node.get("part")
        obj = cls(definitions.wsdl, name, operation, part_name)
        return obj


class MimeMultipart(MimeMessage):
    """The multipart/related MIME type aggregates an arbitrary set of MIME
    formatted parts into one message using the MIME type "multipart/related".

    The mime:multipartRelated element describes the concrete format of such a
    message::

        <mime:multipartRelated>
            <mime:part> *
                <-- mime element -->
            </mime:part>
        </mime:multipartRelated>

    The mime:part element describes each part of a multipart/related message.
    MIME elements appear within mime:part to specify the concrete MIME type for
    the part. If more than one MIME element appears inside a mime:part, they
    are alternatives.

    :param wsdl: The main wsdl document
    :type wsdl: zeep.wsdl.wsdl.Document
    :param name:
    :param operation: The operation to which this message belongs
    :type operation: zeep.wsdl.bindings.soap.SoapOperation
    :param part_name:
    :type type: str

    """

    pass
