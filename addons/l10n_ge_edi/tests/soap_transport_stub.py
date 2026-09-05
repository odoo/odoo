from lxml import etree
from requests import Response

from odoo.tools import file_open, zeep

WSDL_PATH = "l10n_ge_edi/tests/test_files/ntosservice.wsdl"


class SoapTransportStub(zeep.Transport):
    """Answers RS.ge's SOAP calls from recorded envelopes instead of reaching the network.

    Only the two places `zeep` would open a socket are replaced, so everything above them keeps
    running for real: `zeep` reads the WSDL, checks each operation's arguments against it, builds
    the request and deserialises the reply into the object `RSgeClient._call` receives. A
    misspelled parameter, or a change in how Odoo wraps `zeep`, fails here rather than in
    production.

    Responses are the raw XML RS.ge sends back, per operation::

        transport = SoapTransportStub(chek=CHEK_OK)
        transport = SoapTransportStub(get_invoice=[FIRST_CALL, SECOND_CALL])
    """

    def __init__(self, **responses):
        super().__init__()
        self.calls = []
        self.responses = responses

    def load(self, url):
        # EXTENDS zeep: the WSDL, read once when the client is built
        with file_open(WSDL_PATH, "rb") as wsdl:
            return wsdl.read()

    def post(self, address, message, headers):
        # EXTENDS zeep: every operation the client calls leaves through here
        operation = self._operation_of(message)
        self.calls.append((operation, message))
        return self._response_for(operation)

    def operations(self):
        return [operation for operation, _message in self.calls]

    def _operation_of(self, message):
        envelope = etree.fromstring(message if isinstance(message, bytes) else message.encode())
        return etree.QName(envelope.find("{http://schemas.xmlsoap.org/soap/envelope/}Body")[0]).localname

    def _response_for(self, operation):
        content = self.responses.get(operation)
        if isinstance(content, list):
            content = content.pop(0) if len(content) > 1 else content[0]
        if content is None:
            raise AssertionError(f"No recorded RS.ge response for {operation}()")

        response = Response()
        response.status_code = 200
        response.encoding = "utf-8"
        response._content = content if isinstance(content, bytes) else content.encode()
        response.headers["Content-Type"] = "text/xml; charset=utf-8"
        return response
