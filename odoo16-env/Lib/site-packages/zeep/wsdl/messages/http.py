"""
    zeep.wsdl.messages.http
    ~~~~~~~~~~~~~~~~~~~~~~~

"""

from zeep import xsd
from zeep.wsdl.messages.base import ConcreteMessage, SerializedMessage

__all__ = ["UrlEncoded", "UrlReplacement"]


class HttpMessage(ConcreteMessage):
    """Base class for HTTP Binding messages"""

    def resolve(self, definitions, abstract_message):
        self.abstract = abstract_message

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


class UrlEncoded(HttpMessage):
    """The urlEncoded element indicates that all the message parts are encoded
    into the HTTP request URI using the standard URI-encoding rules
    (name1=value&name2=value...).

    The names of the parameters correspond to the names of the message parts.
    Each value contributed by the part is encoded using a name=value pair. This
    may be used with GET to specify URL encoding, or with POST to specify a
    FORM-POST. For GET, the "?" character is automatically appended as
    necessary.

    """

    def serialize(self, *args, **kwargs):
        params = {key: None for key in self.abstract.parts.keys()}
        params.update(zip(self.abstract.parts.keys(), args))
        params.update(kwargs)
        headers = {"Content-Type": "text/xml; charset=utf-8"}
        return SerializedMessage(
            path=self.operation.location, headers=headers, content=params
        )

    @classmethod
    def parse(cls, definitions, xmlelement, operation):
        name = xmlelement.get("name")
        obj = cls(definitions.wsdl, name, operation)
        return obj


class UrlReplacement(HttpMessage):
    """The http:urlReplacement element indicates that all the message parts
    are encoded into the HTTP request URI using a replacement algorithm.

    - The relative URI value of http:operation is searched for a set of search
      patterns.
    - The search occurs before the value of the http:operation is combined with
      the value of the location attribute from http:address.
    - There is one search pattern for each message part. The search pattern
      string is the name of the message part surrounded with parenthesis "("
      and ")".
    - For each match, the value of the corresponding message part is
      substituted for the match at the location of the match.
    - Matches are performed before any values are replaced (replaced values do
      not trigger additional matches).

    Message parts MUST NOT have repeating values.
    <http:urlReplacement/>

    """

    def serialize(self, *args, **kwargs):
        params = {key: None for key in self.abstract.parts.keys()}
        params.update(zip(self.abstract.parts.keys(), args))
        params.update(kwargs)
        headers = {"Content-Type": "text/xml; charset=utf-8"}

        path = self.operation.location
        for key, value in params.items():
            path = path.replace("(%s)" % key, value if value is not None else "")
        return SerializedMessage(path=path, headers=headers, content="")

    @classmethod
    def parse(cls, definitions, xmlelement, operation):
        name = xmlelement.get("name")
        obj = cls(definitions.wsdl, name, operation)
        return obj
