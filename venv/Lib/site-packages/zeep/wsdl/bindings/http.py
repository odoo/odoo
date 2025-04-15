import logging

from lxml import etree

from zeep import ns
from zeep.exceptions import Fault
from zeep.utils import qname_attr
from zeep.wsdl import messages
from zeep.wsdl.definitions import Binding, Operation
from zeep.wsdl.utils import url_http_to_https

logger = logging.getLogger(__name__)

NSMAP = {"http": ns.HTTP, "wsdl": ns.WSDL, "mime": ns.MIME}


class HttpBinding(Binding):
    def create_message(self, operation, *args, **kwargs):
        if isinstance(operation, str):
            operation = self.get(operation)
            if not operation:
                raise ValueError("Operation not found")
        return operation.create(*args, **kwargs)

    def process_service_port(self, xmlelement, force_https=False):
        address_node = xmlelement.find("http:address", namespaces=NSMAP)
        if address_node is None:
            raise ValueError("No `http:address` node found")

        # Force the usage of HTTPS when the force_https boolean is true
        location = address_node.get("location")
        if force_https and location:
            location = url_http_to_https(location)
            if location != address_node.get("location"):
                logger.warning("Forcing http:address location to HTTPS")

        return {"address": location}

    @classmethod
    def parse(cls, definitions, xmlelement):
        name = qname_attr(xmlelement, "name", definitions.target_namespace)
        port_name = qname_attr(xmlelement, "type", definitions.target_namespace)

        obj = cls(definitions.wsdl, name, port_name)
        for node in xmlelement.findall("wsdl:operation", namespaces=NSMAP):
            operation = HttpOperation.parse(definitions, node, obj)
            obj._operation_add(operation)
        return obj

    def process_reply(self, client, operation, response):
        if response.status_code != 200:
            return self.process_error(response.content)
        return operation.process_reply(response.content)

    def process_error(self, doc):
        raise Fault(message=doc)


class HttpPostBinding(HttpBinding):
    def send(self, client, options, operation, args, kwargs):
        """Called from the service"""
        operation_obj = self.get(operation)
        if not operation_obj:
            raise ValueError("Operation %r not found" % operation)

        serialized = operation_obj.create(*args, **kwargs)

        url = options["address"] + serialized.path
        response = client.transport.post(
            url, serialized.content, headers=serialized.headers
        )
        return self.process_reply(client, operation_obj, response)

    @classmethod
    def match(cls, node):
        """Check if this binding instance should be used to parse the given
        node.

        :param node: The node to match against
        :type node: lxml.etree._Element

        """
        http_node = node.find(etree.QName(NSMAP["http"], "binding"))
        return http_node is not None and http_node.get("verb") == "POST"


class HttpGetBinding(HttpBinding):
    def send(self, client, options, operation, args, kwargs):
        """Called from the service"""
        operation_obj = self.get(operation)
        if not operation_obj:
            raise ValueError("Operation %r not found" % operation)

        serialized = operation_obj.create(*args, **kwargs)

        url = options["address"] + serialized.path
        response = client.transport.get(
            url, serialized.content, headers=serialized.headers
        )
        return self.process_reply(client, operation_obj, response)

    @classmethod
    def match(cls, node):
        """Check if this binding instance should be used to parse the given
        node.

        :param node: The node to match against
        :type node: lxml.etree._Element

        """
        http_node = node.find(etree.QName(ns.HTTP, "binding"))
        return http_node is not None and http_node.get("verb") == "GET"


class HttpOperation(Operation):
    def __init__(self, name, binding, location):
        super().__init__(name, binding)
        self.location = location

    def process_reply(self, envelope):
        return self.output.deserialize(envelope)

    @classmethod
    def parse(cls, definitions, xmlelement, binding):
        """

        <wsdl:operation name="GetLastTradePrice">
          <http:operation location="GetLastTradePrice"/>
          <wsdl:input>
            <mime:content type="application/x-www-form-urlencoded"/>
          </wsdl:input>
          <wsdl:output>
            <mime:mimeXml/>
          </wsdl:output>
        </wsdl:operation>

        """
        name = xmlelement.get("name")

        http_operation = xmlelement.find("http:operation", namespaces=NSMAP)
        location = http_operation.get("location")
        obj = cls(name, binding, location)

        for node in xmlelement:
            tag_name = etree.QName(node.tag).localname
            if tag_name not in ("input", "output"):
                continue

            # XXX Multiple mime types may be declared as alternatives
            message_node = None
            nodes = list(node)
            if len(nodes) > 0:
                message_node = nodes[0]
            message_class = None
            if message_node is not None:
                if message_node.tag == etree.QName(ns.HTTP, "urlEncoded"):
                    message_class = messages.UrlEncoded
                elif message_node.tag == etree.QName(ns.HTTP, "urlReplacement"):
                    message_class = messages.UrlReplacement
                elif message_node.tag == etree.QName(ns.MIME, "content"):
                    message_class = messages.MimeContent
                elif message_node.tag == etree.QName(ns.MIME, "mimeXml"):
                    message_class = messages.MimeXML

            if message_class:
                msg = message_class.parse(definitions, node, obj)
                assert msg
                setattr(obj, tag_name, msg)
        return obj

    def resolve(self, definitions):
        super().resolve(definitions)
        if self.output:
            self.output.resolve(definitions, self.abstract.output_message)
        if self.input:
            self.input.resolve(definitions, self.abstract.input_message)
