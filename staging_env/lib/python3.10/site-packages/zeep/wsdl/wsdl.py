"""
    zeep.wsdl.wsdl
    ~~~~~~~~~~~~~~

"""
from __future__ import print_function

import logging
import operator
import os
import typing
import warnings
from collections import OrderedDict

from lxml import etree

from zeep.exceptions import IncompleteMessage
from zeep.loader import (
    absolute_location,
    is_relative_path,
    load_external,
    load_external_async,
)
from zeep.settings import Settings
from zeep.utils import findall_multiple_ns
from zeep.wsdl import parse
from zeep.wsdl.definitions import Binding, PortType, Service
from zeep.xsd import Schema

if typing.TYPE_CHECKING:
    from zeep.transports import Transport

NSMAP = {"wsdl": "http://schemas.xmlsoap.org/wsdl/"}

logger = logging.getLogger(__name__)


class Document:
    """A WSDL Document exists out of one or more definitions.

    There is always one 'root' definition which should be passed as the
    location to the Document.  This definition can import other definitions.
    These imports are non-transitive, only the definitions defined in the
    imported document are available in the parent definition.  This Document is
    mostly just a simple interface to the root definition.

    After all definitions are loaded the definitions are resolved. This
    resolves references which were not yet available during the initial
    parsing phase.


    :param location: Location of this WSDL
    :type location: string
    :param transport: The transport object to be used
    :type transport: zeep.transports.Transport
    :param base: The base location of this document
    :type base: str
    :param strict: Indicates if strict mode is enabled
    :type strict: bool

    """

    def __init__(
        self, location, transport: typing.Type["Transport"], base=None, settings=None
    ):
        """Initialize a WSDL document.

        The root definition properties are exposed as entry points.

        """
        self.settings = settings or Settings()

        if isinstance(location, str):
            if is_relative_path(location):
                location = os.path.abspath(location)
            self.location = location
        else:
            self.location = base

        self.transport = transport

        # Dict with all definition objects within this WSDL
        self._definitions = (
            {}
        )  # type: typing.Dict[typing.Tuple[str, str], "Definition"]
        self.types = Schema(
            node=None,
            transport=self.transport,
            location=self.location,
            settings=self.settings,
        )
        self.load(location)

    def load(self, location):
        document = self._get_xml_document(location)

        root_definitions = Definition(self, document, self.location)
        root_definitions.resolve_imports()

        # Make the wsdl definitions public
        self.messages = root_definitions.messages
        self.port_types = root_definitions.port_types
        self.bindings = root_definitions.bindings
        self.services = root_definitions.services

    def __repr__(self):
        return "<WSDL(location=%r)>" % self.location

    def dump(self):
        print("")
        print("Prefixes:")
        for prefix, namespace in self.types.prefix_map.items():
            print(" " * 4, "%s: %s" % (prefix, namespace))

        print("")
        print("Global elements:")
        for elm_obj in sorted(self.types.elements, key=lambda k: k.qname):
            value = elm_obj.signature(schema=self.types)
            print(" " * 4, value)

        print("")
        print("Global types:")
        for type_obj in sorted(self.types.types, key=lambda k: k.qname or ""):
            value = type_obj.signature(schema=self.types)
            print(" " * 4, value)

        print("")
        print("Bindings:")
        for binding_obj in sorted(self.bindings.values(), key=lambda k: str(k)):
            print(" " * 4, str(binding_obj))

        print("")
        for service in self.services.values():
            print(str(service))
            for port in service.ports.values():
                print(" " * 4, str(port))
                print(" " * 8, "Operations:")

                operations = sorted(
                    port.binding._operations.values(), key=operator.attrgetter("name")
                )

                for operation in operations:
                    print("%s%s" % (" " * 12, str(operation)))
                print("")

    def _get_xml_document(self, location: typing.IO) -> etree._Element:
        """Load the XML content from the given location and return an
        lxml.Element object.

        :param location: The URL of the document to load
        :type location: string

        """
        return load_external(
            location, self.transport, self.location, settings=self.settings
        )

    def _add_definition(self, definition: "Definition"):
        key = (definition.target_namespace, definition.location)
        self._definitions[key] = definition


class Definition:
    """The Definition represents one wsdl:definition within a Document.

    :param wsdl: The wsdl

    """

    def __init__(self, wsdl, doc, location):
        """fo

        :param wsdl: The wsdl

        """
        logger.debug("Creating definition for %s", location)
        self.wsdl = wsdl
        self.location = location

        self.types = wsdl.types
        self.port_types = {}
        self.messages = {}
        self.bindings = {}  # type: typing.Dict[str, typing.Type[Binding]]
        self.services = OrderedDict()  # type: typing.Dict[str, Service]

        self.imports = {}
        self._resolved_imports = False

        self.target_namespace = doc.get("targetNamespace")
        self.wsdl._add_definition(self)
        self.nsmap = doc.nsmap
        self._load(doc)

    def _load(self, doc):
        self.parse_imports(doc)

        self.parse_types(doc)
        self.messages = self.parse_messages(doc)
        self.port_types = self.parse_ports(doc)
        self.bindings = self.parse_binding(doc)
        self.services = self.parse_service(doc)

    def __repr__(self):
        return "<%s(location=%r)>" % (self.__class__.__name__, self.location)

    def get(self, name, key, _processed=None):
        container = getattr(self, name)
        if key in container:
            return container[key]

        # Turns out that no one knows if the wsdl import statement is
        # transitive or not. WSDL/SOAP specs are awesome... So lets just do it.
        # TODO: refactor me into something more sane
        _processed = _processed or set()
        if self.target_namespace not in _processed:
            _processed.add(self.target_namespace)
            for definition in self.imports.values():
                try:
                    return definition.get(name, key, _processed)
                except IndexError:
                    # Try to see if there is an item which has no namespace
                    # but where the localname matches. This is basically for
                    # #356 but in the future we should also ignore mismatching
                    # namespaces as last fallback
                    fallback_key = etree.QName(key).localname
                    try:
                        return definition.get(name, fallback_key, _processed)
                    except IndexError:
                        pass

        raise IndexError("No definition %r in %r found" % (key, name))

    def resolve_imports(self) -> None:
        """Resolve all root elements (types, messages, etc)."""

        # Simple guard to protect against cyclic imports
        if self._resolved_imports:
            return
        self._resolved_imports = True

        for definition in self.imports.values():
            definition.resolve_imports()

        for message in self.messages.values():
            message.resolve(self)

        for port_type in self.port_types.values():
            port_type.resolve(self)

        for binding in self.bindings.values():
            binding.resolve(self)

        for service in self.services.values():
            service.resolve(self)

    def parse_imports(self, doc):
        """Import other WSDL definitions in this document.

        Note that imports are non-transitive, so only import definitions
        which are defined in the imported document and ignore definitions
        imported in that document.

        This should handle recursive imports though:

            A -> B -> A
            A -> B -> C -> A

        :param doc: The source document
        :type doc: lxml.etree._Element

        """
        for import_node in doc.findall("wsdl:import", namespaces=NSMAP):
            namespace = import_node.get("namespace")
            location = import_node.get("location")

            if not location:
                logger.debug(
                    "Skipping import for namespace %s (empty location)", namespace
                )
                continue

            location = absolute_location(location, self.location)
            key = (namespace, location)
            if key in self.wsdl._definitions:
                self.imports[key] = self.wsdl._definitions[key]
            else:
                document = self.wsdl._get_xml_document(location)
                if etree.QName(document.tag).localname == "schema":
                    self.types.add_documents([document], location)
                else:
                    wsdl = Definition(self.wsdl, document, location)
                    self.imports[key] = wsdl

    def parse_types(self, doc):
        """Return an xsd.Schema() instance for the given wsdl:types element.

        If the wsdl:types contain multiple schema definitions then a new
        wrapping xsd.Schema is defined with xsd:import statements linking them
        together.

        If the wsdl:types doesn't container an xml schema then an empty schema
        is returned instead.

        Definition::

            <definitions .... >
                <types>
                    <xsd:schema .... />*
                </types>
            </definitions>

        :param doc: The source document
        :type doc: lxml.etree._Element

        """
        namespace_sets = [
            {
                "xsd": "http://www.w3.org/2001/XMLSchema",
                "wsdl": "http://schemas.xmlsoap.org/wsdl/",
            },
            {
                "xsd": "http://www.w3.org/1999/XMLSchema",
                "wsdl": "http://schemas.xmlsoap.org/wsdl/",
            },
        ]

        # Find xsd:schema elements (wsdl:types/xsd:schema)
        schema_nodes = findall_multiple_ns(doc, "wsdl:types/xsd:schema", namespace_sets)
        self.types.add_documents(schema_nodes, self.location)

    def parse_messages(self, doc: etree._Element):
        """

        Definition::

            <definitions .... >
                <message name="nmtoken"> *
                    <part name="nmtoken" element="qname"? type="qname"?/> *
                </message>
            </definitions>

        :param doc: The source document
        :type doc: lxml.etree._Element

        """
        result = {}
        for msg_node in doc.findall("wsdl:message", namespaces=NSMAP):
            try:
                msg = parse.parse_abstract_message(self, msg_node)
            except IncompleteMessage as exc:
                warnings.warn(str(exc))
            else:
                result[msg.name.text] = msg
                logger.debug("Adding message: %s", msg.name.text)
        return result

    def parse_ports(self, doc: etree._Element) -> typing.Dict[str, PortType]:
        """Return dict with `PortType` instances as values

        Definition::

            <wsdl:definitions .... >
                <wsdl:portType name="nmtoken">
                    <wsdl:operation name="nmtoken" .... /> *
                </wsdl:portType>
            </wsdl:definitions>

        :param doc: The source document
        :type doc: lxml.etree._Element

        """
        result = {}
        for port_node in doc.findall("wsdl:portType", namespaces=NSMAP):
            port_type = parse.parse_port_type(self, port_node)
            result[port_type.name.text] = port_type
            logger.debug("Adding port: %s", port_type.name.text)
        return result

    def parse_binding(
        self, doc: etree._Element
    ) -> typing.Dict[str, typing.Type[Binding]]:
        """Parse the binding elements and return a dict of bindings.

        Currently supported bindings are Soap 1.1, Soap 1.2., HTTP Get and
        HTTP Post. The detection of the type of bindings is done by the
        bindings themselves using the introspection of the xml nodes.

        Definition::

            <wsdl:definitions .... >
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
            </wsdl:definitions>

        :param doc: The source document
        :type doc: lxml.etree._Element
        :returns: Dictionary with binding name as key and Binding instance as
          value
        :rtype: dict

        """
        result = {}
        binding_classes = []  # type: typing.List[typing.Type[Binding]]

        if not getattr(self.wsdl.transport, "binding_classes", None):
            from zeep.wsdl import bindings

            binding_classes = [
                bindings.Soap11Binding,
                bindings.Soap12Binding,
                bindings.HttpGetBinding,
                bindings.HttpPostBinding,
            ]
        else:
            binding_classes = self.wsdl.transport.binding_classes

        for binding_node in doc.findall("wsdl:binding", namespaces=NSMAP):
            # Detect the binding type
            binding = None
            for binding_class in binding_classes:
                if binding_class.match(binding_node):

                    try:
                        binding = binding_class.parse(self, binding_node)
                    except NotImplementedError as exc:
                        logger.debug("Ignoring binding: %s", exc)
                        continue

                    logger.debug("Adding binding: %s", binding.name.text)
                    result[binding.name.text] = binding
                    break
        return result

    def parse_service(self, doc: etree._Element) -> typing.Dict[str, Service]:
        """

        Definition::

            <wsdl:definitions .... >
                <wsdl:service .... > *
                    <wsdl:port name="nmtoken" binding="qname"> *
                       <-- extensibility element (1) -->
                    </wsdl:port>
                </wsdl:service>
            </wsdl:definitions>

        :param doc: The source document
        :type doc: lxml.etree._Element

        """
        result = OrderedDict()
        for service_node in doc.findall("wsdl:service", namespaces=NSMAP):
            service = parse.parse_service(self, service_node)
            result[service.name] = service
            logger.debug("Adding service: %s", service.name)
        return result
