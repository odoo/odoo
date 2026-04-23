import uuid

from lxml import etree
from lxml.builder import ElementMaker

from zeep import ns
from zeep.plugins import Plugin
from zeep.wsdl.utils import get_or_create_header

WSA = ElementMaker(namespace=ns.WSA, nsmap={"wsa": ns.WSA})


class WsAddressingPlugin(Plugin):
    nsmap = {"wsa": ns.WSA}

    def egress(self, envelope, http_headers, operation, binding_options):
        """Apply the ws-addressing headers to the given envelope."""

        wsa_action = operation.abstract.wsa_action
        if not wsa_action:
            wsa_action = operation.soapaction

        header = get_or_create_header(envelope)
        headers = [
            WSA.Action(wsa_action),
            WSA.MessageID("urn:uuid:" + str(uuid.uuid4())),
            WSA.To(binding_options["address"]),
        ]
        header.extend(headers)

        # the top_nsmap kwarg was added in lxml 3.5.0
        if etree.LXML_VERSION[:2] >= (3, 5):
            etree.cleanup_namespaces(
                header, keep_ns_prefixes=header.nsmap, top_nsmap=self.nsmap
            )
        else:
            etree.cleanup_namespaces(header)
        return envelope, http_headers
