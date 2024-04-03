import logging
import typing

from lxml import etree
from requests_toolbelt.multipart.decoder import MultipartDecoder

from zeep import ns, plugins, wsa
from zeep.exceptions import Fault, TransportError, XMLSyntaxError
from zeep.loader import parse_xml
from zeep.utils import as_qname, get_media_type, qname_attr
from zeep.wsdl.attachments import MessagePack
from zeep.wsdl.definitions import Binding, Operation
from zeep.wsdl.messages import DocumentMessage, RpcMessage
from zeep.wsdl.messages.xop import process_xop
from zeep.wsdl.utils import etree_to_string, url_http_to_https

if typing.TYPE_CHECKING:
    from zeep.wsdl.wsdl import Definition


logger = logging.getLogger(__name__)


class SoapBinding(Binding):
    """Soap 1.1/1.2 binding"""

    def __init__(self, wsdl, name, port_name, transport, default_style):
        """The SoapBinding is the base class for the Soap11Binding and
        Soap12Binding.

        :param wsdl:
        :type wsdl:
        :param name:
        :type name: string
        :param port_name:
        :type port_name: string
        :param transport:
        :type transport: zeep.transports.Transport
        :param default_style:

        """
        super().__init__(wsdl, name, port_name)
        self.transport = transport
        self.default_style = default_style

    @classmethod
    def match(cls, node):
        """Check if this binding instance should be used to parse the given
        node.

        :param node: The node to match against
        :type node: lxml.etree._Element

        """
        soap_node = node.find("soap:binding", namespaces=cls.nsmap)
        return soap_node is not None

    def create_message(self, operation, *args, **kwargs):
        envelope, http_headers = self._create(operation, args, kwargs)
        return envelope

    def _create(self, operation, args, kwargs, client=None, options=None):
        """Create the XML document to send to the server.

        Note that this generates the soap envelope without the wsse applied.

        """
        operation_obj = self.get(operation)
        if not operation_obj:
            raise ValueError("Operation %r not found" % operation)

        # Create the SOAP envelope
        serialized = operation_obj.create(*args, **kwargs)
        self._set_http_headers(serialized, operation_obj)

        envelope = serialized.content
        http_headers = serialized.headers

        # Apply ws-addressing
        if client:
            if not options:
                options = client.service._binding_options

            if operation_obj.abstract.wsa_action:
                envelope, http_headers = wsa.WsAddressingPlugin().egress(
                    envelope, http_headers, operation_obj, options
                )

            # Apply plugins
            envelope, http_headers = plugins.apply_egress(
                client, envelope, http_headers, operation_obj, options
            )

            # Apply WSSE
            if client.wsse:
                if isinstance(client.wsse, list):
                    for wsse in client.wsse:
                        envelope, http_headers = wsse.apply(envelope, http_headers)
                else:
                    envelope, http_headers = client.wsse.apply(envelope, http_headers)

        # Add extra http headers from the setings object
        if client.settings.extra_http_headers:
            http_headers.update(client.settings.extra_http_headers)

        return envelope, http_headers

    def send(self, client, options, operation, args, kwargs):
        """Called from the service

        :param client: The client with which the operation was called
        :type client: zeep.client.Client
        :param options: The binding options
        :type options: dict
        :param operation: The operation object from which this is a reply
        :type operation: zeep.wsdl.definitions.Operation
        :param args: The args to pass to the operation
        :type args: tuple
        :param kwargs: The kwargs to pass to the operation
        :type kwargs: dict

        """
        envelope, http_headers = self._create(
            operation, args, kwargs, client=client, options=options
        )

        response = client.transport.post_xml(options["address"], envelope, http_headers)

        operation_obj = self.get(operation)

        # If the client wants to return the raw data then let's do that.
        if client.settings.raw_response:
            return response

        return self.process_reply(client, operation_obj, response)

    async def send_async(self, client, options, operation, args, kwargs):
        """Called from the async service

        :param client: The client with which the operation was called
        :type client: zeep.client.Client
        :param options: The binding options
        :type options: dict
        :param operation: The operation object from which this is a reply
        :type operation: zeep.wsdl.definitions.Operation
        :param args: The args to pass to the operation
        :type args: tuple
        :param kwargs: The kwargs to pass to the operation
        :type kwargs: dict

        """
        envelope, http_headers = self._create(
            operation, args, kwargs, client=client, options=options
        )

        response = await client.transport.post_xml(
            options["address"], envelope, http_headers
        )

        if client.settings.raw_response:
            return response

        operation_obj = self.get(operation)
        return self.process_reply(client, operation_obj, response)

    def process_reply(self, client, operation, response):
        """Process the XML reply from the server.

        :param client: The client with which the operation was called
        :type client: zeep.client.Client
        :param operation: The operation object from which this is a reply
        :type operation: zeep.wsdl.definitions.Operation
        :param response: The response object returned by the remote server
        :type response: requests.Response

        """
        if response.status_code in (201, 202) and not response.content:
            return None

        elif response.status_code != 200 and not response.content:
            raise TransportError(
                u"Server returned HTTP status %d (no content available)"
                % response.status_code,
                status_code=response.status_code,
            )

        content_type = response.headers.get("Content-Type", "text/xml")
        media_type = get_media_type(content_type)
        message_pack = None

        # If the reply is a multipart/related then we need to retrieve all the
        # parts
        if media_type == "multipart/related":
            decoder = MultipartDecoder(
                response.content, content_type, response.encoding or "utf-8"
            )
            content = decoder.parts[0].content
            if len(decoder.parts) > 1:
                message_pack = MessagePack(parts=decoder.parts[1:])
        else:
            content = response.content

        try:
            doc = parse_xml(content, self.transport, settings=client.settings)
        except XMLSyntaxError as exc:
            raise TransportError(
                "Server returned response (%s) with invalid XML: %s.\nContent: %r"
                % (response.status_code, exc, response.content),
                status_code=response.status_code,
                content=response.content,
            )

        # Check if this is an XOP message which we need to decode first
        if message_pack:
            if process_xop(doc, message_pack):
                message_pack = None

        if client.wsse:
            client.wsse.verify(doc)

        doc, http_headers = plugins.apply_ingress(
            client, doc, response.headers, operation
        )

        # If the response code is not 200 or if there is a Fault node available
        # then assume that an error occured.
        fault_node = doc.find("soap-env:Body/soap-env:Fault", namespaces=self.nsmap)
        if response.status_code != 200 or fault_node is not None:
            return self.process_error(doc, operation)

        result = operation.process_reply(doc)

        if message_pack:
            message_pack._set_root(result)
            return message_pack
        return result

    def process_error(self, doc, operation):
        raise NotImplementedError

    def process_service_port(self, xmlelement, force_https=False):
        address_node = xmlelement.find("soap:address", namespaces=self.nsmap)
        if address_node is None:
            logger.debug("No valid soap:address found for service")
            return

        # Force the usage of HTTPS when the force_https boolean is true
        location = address_node.get("location")
        if force_https and location:
            location = url_http_to_https(location)
            if location != address_node.get("location"):
                logger.warning("Forcing soap:address location to HTTPS")

        return {"address": location}

    @classmethod
    def parse(cls, definitions, xmlelement):
        """

        Definition::

            <wsdl:binding name="nmtoken" type="qname"> *
                <-- extensibility element (1) --> *
                <wsdl:operation name="nmtoken"> *
                   <-- extensibility element (2) --> *
                   <wsdl:input name="nmtoken"? > ?
                       <-- extensibility element (3) -->
                   </wsdl:input>
                   <wsdl:output name="nmtoken"? > ?
                       <-- extensibility element (4) --> *
                   </wsdl:output>
                   <wsdl:fault name="nmtoken"> *
                       <-- extensibility element (5) --> *
                   </wsdl:fault>
                </wsdl:operation>
            </wsdl:binding>
        """
        name = qname_attr(xmlelement, "name", definitions.target_namespace)
        port_name = qname_attr(xmlelement, "type", definitions.target_namespace)

        # The soap:binding element contains the transport method and
        # default style attribute for the operations.
        soap_node = xmlelement.find("soap:binding", namespaces=cls.nsmap)
        transport = soap_node.get("transport")

        supported_transports = [
            "http://schemas.xmlsoap.org/soap/http",
            "http://www.w3.org/2003/05/soap/bindings/HTTP/",
        ]

        if transport not in supported_transports:
            raise NotImplementedError(
                "The binding transport %s is not supported (only soap/http)"
                % (transport)
            )
        default_style = soap_node.get("style", "document")

        obj = cls(definitions.wsdl, name, port_name, transport, default_style)
        for node in xmlelement.findall("wsdl:operation", namespaces=cls.nsmap):
            operation = SoapOperation.parse(definitions, node, obj, nsmap=cls.nsmap)
            obj._operation_add(operation)
        return obj


class Soap11Binding(SoapBinding):
    nsmap = {
        "soap": ns.SOAP_11,
        "soap-env": ns.SOAP_ENV_11,
        "wsdl": ns.WSDL,
        "xsd": ns.XSD,
    }

    def process_error(self, doc, operation):
        fault_node = doc.find("soap-env:Body/soap-env:Fault", namespaces=self.nsmap)

        if fault_node is None:
            raise Fault(
                message="Unknown fault occured",
                code=None,
                actor=None,
                detail=etree_to_string(doc),
            )

        def get_text(name):
            child = fault_node.find(name, namespaces=fault_node.nsmap)
            if child is not None:
                return child.text

        raise Fault(
            message=get_text("faultstring"),
            code=get_text("faultcode"),
            actor=get_text("faultactor"),
            detail=fault_node.find("detail", namespaces=fault_node.nsmap),
        )

    def _set_http_headers(self, serialized, operation):
        serialized.headers["Content-Type"] = "text/xml; charset=utf-8"


class Soap12Binding(SoapBinding):
    nsmap = {
        "soap": ns.SOAP_12,
        "soap-env": ns.SOAP_ENV_12,
        "wsdl": ns.WSDL,
        "xsd": ns.XSD,
    }

    def process_error(self, doc, operation):
        fault_node = doc.find("soap-env:Body/soap-env:Fault", namespaces=self.nsmap)

        if fault_node is None:
            raise Fault(
                message="Unknown fault occured",
                code=None,
                actor=None,
                detail=etree_to_string(doc),
            )

        def get_text(name):
            child = fault_node.find(name)
            if child is not None:
                return child.text

        message = fault_node.findtext(
            "soap-env:Reason/soap-env:Text", namespaces=self.nsmap
        )
        code = fault_node.findtext(
            "soap-env:Code/soap-env:Value", namespaces=self.nsmap
        )

        # Extract the fault subcodes. These can be nested, as in subcodes can
        # also contain other subcodes.
        subcodes = []
        subcode_element = fault_node.find(
            "soap-env:Code/soap-env:Subcode", namespaces=self.nsmap
        )
        while subcode_element is not None:
            subcode_value_element = subcode_element.find(
                "soap-env:Value", namespaces=self.nsmap
            )
            subcode_qname = as_qname(
                subcode_value_element.text, subcode_value_element.nsmap, None
            )
            subcodes.append(subcode_qname)
            subcode_element = subcode_element.find(
                "soap-env:Subcode", namespaces=self.nsmap
            )

        # TODO: We should use the fault message as defined in the wsdl.
        detail_node = fault_node.find("soap-env:Detail", namespaces=self.nsmap)
        raise Fault(
            message=message,
            code=code,
            actor=None,
            detail=detail_node,
            subcodes=subcodes,
        )

    def _set_http_headers(self, serialized, operation):
        serialized.headers["Content-Type"] = "; ".join(
            [
                "application/soap+xml",
                "charset=utf-8",
                'action="%s"' % operation.soapaction,
            ]
        )


class SoapOperation(Operation):
    """Represent's an operation within a specific binding."""

    def __init__(self, name, binding, nsmap, soapaction, style):
        super().__init__(name, binding)
        self.nsmap = nsmap
        self.soapaction = soapaction
        self.style = style

    def process_reply(self, envelope):
        envelope_qname = etree.QName(self.nsmap["soap-env"], "Envelope")
        if envelope.tag != envelope_qname:
            raise XMLSyntaxError(
                (
                    "The XML returned by the server does not contain a valid "
                    + "{%s}Envelope root element. The root element found is %s "
                )
                % (envelope_qname.namespace, envelope.tag)
            )

        if self.output:
            return self.output.deserialize(envelope)

    @classmethod
    def parse(cls, definitions, xmlelement, binding, nsmap):
        """

        Definition::

            <wsdl:operation name="nmtoken"> *
                <soap:operation soapAction="uri"? style="rpc|document"?>?
                <wsdl:input name="nmtoken"? > ?
                    <soap:body use="literal"/>
               </wsdl:input>
               <wsdl:output name="nmtoken"? > ?
                    <-- extensibility element (4) --> *
               </wsdl:output>
               <wsdl:fault name="nmtoken"> *
                    <-- extensibility element (5) --> *
               </wsdl:fault>
            </wsdl:operation>

        Example::

            <wsdl:operation name="GetLastTradePrice">
              <soap:operation soapAction="http://example.com/GetLastTradePrice"/>
              <wsdl:input>
                <soap:body use="literal"/>
              </wsdl:input>
              <wsdl:output>
              </wsdl:output>
              <wsdl:fault name="dataFault">
                <soap:fault name="dataFault" use="literal"/>
              </wsdl:fault>
            </operation>

        """
        name = xmlelement.get("name")

        # The soap:operation element is required for soap/http bindings
        # and may be omitted for other bindings.
        soap_node = xmlelement.find("soap:operation", namespaces=binding.nsmap)
        action = None
        if soap_node is not None:
            action = soap_node.get("soapAction")
            style = soap_node.get("style", binding.default_style)
        else:
            style = binding.default_style

        obj = cls(name, binding, nsmap, action, style)

        if style == "rpc":
            message_class = RpcMessage
        else:
            message_class = DocumentMessage

        for node in xmlelement:
            tag_name = etree.QName(node.tag).localname
            if tag_name not in ("input", "output", "fault"):
                continue
            msg = message_class.parse(
                definitions=definitions,
                xmlelement=node,
                operation=obj,
                nsmap=nsmap,
                type=tag_name,
            )
            if tag_name == "fault":
                obj.faults[msg.name] = msg
            else:
                setattr(obj, tag_name, msg)

        return obj

    def resolve(self, definitions: "Definition"):
        super().resolve(definitions)
        for name, fault in self.faults.items():
            if name in self.abstract.fault_messages:
                fault.resolve(definitions, self.abstract.fault_messages[name])

        if self.output:
            self.output.resolve(definitions, self.abstract.output_message)
        if self.input:
            self.input.resolve(definitions, self.abstract.input_message)
