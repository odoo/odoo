import logging
import typing
from collections import OrderedDict

from lxml import etree

from zeep import exceptions, ns
from zeep.loader import load_external
from zeep.settings import Settings
from zeep.xsd import const
from zeep.xsd import elements as xsd_elements
from zeep.xsd import types as xsd_types
from zeep.xsd.elements import builtins as xsd_builtins_elements
from zeep.xsd.types import builtins as xsd_builtins_types
from zeep.xsd.visitor import SchemaVisitor

logger = logging.getLogger(__name__)


class Schema:
    """A schema is a collection of schema documents."""

    def __init__(self, node=None, transport=None, location=None, settings=None):
        """
        :param node:
        :param transport:
        :param location:
        :param settings: The settings object

        """
        self.settings = settings or Settings()

        self._transport = transport

        self.documents = _SchemaContainer()
        self._prefix_map_auto = {}
        self._prefix_map_custom = {}

        self._load_default_documents()

        if not isinstance(node, list):
            nodes = [node] if node is not None else []
        else:
            nodes = node
        self.add_documents(nodes, location)

    def __repr__(self):
        main_doc = self.root_document
        if main_doc:
            return "<Schema(location=%r, tns=%r)>" % (
                main_doc._location,
                main_doc._target_namespace,
            )
        return "<Schema()>"

    @property
    def prefix_map(self):
        retval = {}
        retval.update(self._prefix_map_custom)
        retval.update(
            {k: v for k, v in self._prefix_map_auto.items() if v not in retval.values()}
        )
        return retval

    @property
    def root_document(self):
        return next((doc for doc in self.documents if not doc._is_internal), None)

    @property
    def is_empty(self):
        """Boolean to indicate if this schema contains any types or elements"""
        return all(document.is_empty for document in self.documents)

    @property
    def namespaces(self):
        return self.documents.get_all_namespaces()

    @property
    def elements(self):
        """Yield all globla xsd.Type objects

        :rtype: Iterable of zeep.xsd.Element

        """
        seen = set()
        for document in self.documents:
            for element in document._elements.values():
                if element.qname not in seen:
                    yield element
                    seen.add(element.qname)

    @property
    def types(self):
        """Yield all global xsd.Type objects

        :rtype: Iterable of zeep.xsd.ComplexType

        """
        seen = set()
        for document in self.documents:
            for type_ in document._types.values():
                if type_.qname not in seen:
                    yield type_
                    seen.add(type_.qname)

    def add_documents(
        self, schema_nodes: typing.List[etree._Element], location: str
    ) -> None:
        resolve_queue = []
        for node in schema_nodes:
            document = self.create_new_document(node, location)
            resolve_queue.append(document)

        for document in resolve_queue:
            document.resolve()

        self._prefix_map_auto = self._create_prefix_map()

    def add_document_by_url(self, url: str) -> None:
        schema_node = load_external(url, self._transport, settings=self.settings)
        document = self.create_new_document(schema_node, url=url)
        document.resolve()

    def get_element(self, qname) -> xsd_elements.Element:
        """Return a global xsd.Element object with the given qname"""
        qname = self._create_qname(qname)
        return self._get_instance(qname, "get_element", "element")

    def get_type(self, qname, fail_silently=False):
        """Return a global xsd.Type object with the given qname

        :rtype: zeep.xsd.ComplexType or zeep.xsd.AnySimpleType


        """
        qname = self._create_qname(qname)
        try:
            return self._get_instance(qname, "get_type", "type")
        except exceptions.NamespaceError as exc:
            if fail_silently:
                logger.debug(str(exc))
            else:
                raise

    def get_group(self, qname) -> xsd_elements.Group:
        """Return a global xsd.Group object with the given qname."""
        return self._get_instance(qname, "get_group", "group")

    def get_attribute(self, qname) -> xsd_elements.Attribute:
        """Return a global xsd.attribute object with the given qname"""
        return self._get_instance(qname, "get_attribute", "attribute")

    def get_attribute_group(self, qname) -> xsd_elements.AttributeGroup:
        """Return a global xsd.attributeGroup object with the given qname"""
        return self._get_instance(qname, "get_attribute_group", "attributeGroup")

    def set_ns_prefix(self, prefix, namespace):
        self._prefix_map_custom[prefix] = namespace

    def get_ns_prefix(self, prefix):
        try:
            try:
                return self._prefix_map_custom[prefix]
            except KeyError:
                return self._prefix_map_auto[prefix]
        except KeyError:
            raise ValueError("No such prefix %r" % prefix)

    def get_shorthand_for_ns(self, namespace):
        for prefix, other_namespace in self._prefix_map_auto.items():
            if namespace == other_namespace:
                return prefix
        for prefix, other_namespace in self._prefix_map_custom.items():
            if namespace == other_namespace:
                return prefix

        if namespace == "http://schemas.xmlsoap.org/soap/envelope/":
            return "soap-env"
        return namespace

    def create_new_document(self, node, url, base_url=None, target_namespace=None):
        """

        :rtype: zeep.xsd.schema.SchemaDocument

        """
        namespace = node.get("targetNamespace") if node is not None else None
        if not namespace:
            namespace = target_namespace
        if base_url is None:
            base_url = url

        schema = SchemaDocument(namespace, url, base_url)
        self.documents.add(schema)
        schema.load(self, node)
        return schema

    def merge(self, schema):
        """Merge an other XSD schema in this one"""
        for document in schema.documents:
            self.documents.add(document)
        self._prefix_map_auto = self._create_prefix_map()

    def deserialize(self, node):
        elm = self.get_element(node.tag)
        return elm.parse(node, schema=self)

    def _load_default_documents(self):
        schema = SchemaDocument(ns.XSD, None, None)

        for cls in xsd_builtins_types._types:
            instance = cls(is_global=True)
            schema.register_type(cls._default_qname, instance)

        for cls in xsd_builtins_elements._elements:
            instance = cls()
            schema.register_element(cls.qname, instance)

        schema._is_internal = True
        self.documents.add(schema)
        return schema

    def _get_instance(self, qname, method_name, name):
        """Return an object from one of the SchemaDocument's"""
        qname = self._create_qname(qname)
        try:
            last_exception = None  # type: typing.Optional[BaseException]
            for schema in self._get_schema_documents(qname.namespace):
                method = getattr(schema, method_name)
                try:
                    return method(qname)
                except exceptions.LookupError as exc:
                    last_exception = exc
                    continue
            if last_exception is not None:
                raise last_exception

        except exceptions.NamespaceError:
            raise exceptions.NamespaceError(
                (
                    "Unable to resolve %s %s. "
                    + "No schema available for the namespace %r."
                )
                % (name, qname.text, qname.namespace)
            )

    def _create_qname(self, name):
        """Create an `lxml.etree.QName()` object for the given qname string.

        This also expands the shorthand notation.

        :rtype: lxml.etree.QNaame

        """
        if isinstance(name, etree.QName):
            return name

        if not name.startswith("{") and ":" in name and self._prefix_map_auto:
            prefix, localname = name.split(":", 1)
            if prefix in self._prefix_map_custom:
                return etree.QName(self._prefix_map_custom[prefix], localname)
            elif prefix in self._prefix_map_auto:
                return etree.QName(self._prefix_map_auto[prefix], localname)
            else:
                raise ValueError("No namespace defined for the prefix %r" % prefix)
        else:
            return etree.QName(name)

    def _create_prefix_map(self):
        prefix_map = {"xsd": "http://www.w3.org/2001/XMLSchema"}
        i = 0
        for namespace in self.documents.get_all_namespaces():
            if namespace is None or namespace in prefix_map.values():
                continue

            prefix_map["ns%d" % i] = namespace
            i += 1
        return prefix_map

    def _get_schema_documents(self, namespace, fail_silently=False):
        """Return a list of SchemaDocument's for the given namespace.

        :rtype: list of SchemaDocument

        """
        if (
            not self.documents.has_schema_document_for_ns(namespace)
            and namespace in const.AUTO_IMPORT_NAMESPACES
        ):
            logger.debug("Auto importing missing known schema: %s", namespace)
            self.add_document_by_url(namespace)

        return self.documents.get_by_namespace(namespace, fail_silently)


class _SchemaContainer:
    """Container instances to store multiple SchemaDocument objects per
    namespace.

    """

    def __init__(self):
        self._instances = OrderedDict()

    def __iter__(self):
        yield from self.values()

    def add(self, document: "SchemaDocument") -> None:
        """Add a schema document"""
        logger.debug(
            "Add document with tns %s to schema %s", document.namespace, id(self)
        )
        documents = self._instances.setdefault(document.namespace, [])
        documents.append(document)

    def get_all_namespaces(self) -> typing.List[str]:
        return list(self._instances.keys())

    def get_by_namespace(
        self, namespace, fail_silently
    ) -> typing.List["SchemaDocument"]:
        if namespace not in self._instances:
            if fail_silently:
                return []
            raise exceptions.NamespaceError(
                "No schema available for the namespace %r" % namespace
            )
        return self._instances[namespace]

    def get_by_namespace_and_location(
        self, namespace: str, location: str
    ) -> typing.Optional["SchemaDocument"]:
        """Return a SchemaDocument for the given namespace AND location"""
        documents = self.get_by_namespace(namespace, fail_silently=True)
        for document in documents:
            if document._location == location:
                return document
        return None

    def has_schema_document_for_ns(self, namespace: str) -> bool:
        """Return a boolean if there is a SchemaDocument for the namespace.

        :rtype: boolean

        """
        return namespace in self._instances

    def values(self):
        for documents in self._instances.values():
            yield from documents


class SchemaDocument:
    """A Schema Document consists of a set of schema components for a
    specific target namespace.

    This represents an xsd:Schema object

    """

    def __init__(self, namespace, location, base_url):
        logger.debug("Init schema document for %r", location)

        # Internal
        self._base_url = base_url or location
        self._location = location
        self._target_namespace = namespace
        self._is_internal = False
        self._has_empty_import = False

        # Containers for specific types
        self._attribute_groups = {}
        self._attributes = {}
        self._elements = {}
        self._groups = {}
        self._types = {}

        self._imports = OrderedDict()
        self._element_form = "unqualified"
        self._attribute_form = "unqualified"
        self._resolved = False
        # self._xml_schema = None

    def __repr__(self):
        return "<SchemaDocument(location=%r, tns=%r, is_empty=%r)>" % (
            self._location,
            self._target_namespace,
            self.is_empty,
        )

    @property
    def namespace(self):
        return self._target_namespace

    @property
    def is_empty(self):
        return not bool(self._imports or self._types or self._elements)

    def load(self, schema, node):
        """Load the XML Schema passed in via the node attribute.

        :type schema: zeep.xsd.schema.Schema
        :type node: etree._Element

        """
        if node is None:
            return

        if not schema.documents.has_schema_document_for_ns(self._target_namespace):
            raise RuntimeError(
                "The document needs to be registered in the schema before "
                + "it can be loaded"
            )

        # Disable XML schema validation for now
        # if len(node) > 0:
        #     self.xml_schema = etree.XMLSchema(node)
        visitor = SchemaVisitor(schema, self)
        visitor.visit_schema(node)

    def resolve(self):
        logger.debug("Resolving in schema %s", self)

        if self._resolved:
            return
        self._resolved = True

        for schemas in self._imports.values():
            for schema in schemas:
                schema.resolve()

        def _resolve_dict(val):
            try:
                for key, obj in val.items():
                    new = obj.resolve()
                    assert new is not None, "resolve() should return an object"
                    val[key] = new
            except exceptions.LookupError as exc:
                raise exceptions.LookupError(
                    (
                        "Unable to resolve %(item_name)s %(qname)s in "
                        "%(file)s. (via %(parent)s)"
                    )
                    % {
                        "item_name": exc.item_name,
                        "qname": exc.qname,
                        "file": exc.location,
                        "parent": obj.qname,
                    }
                )

        _resolve_dict(self._attribute_groups)
        _resolve_dict(self._attributes)
        _resolve_dict(self._elements)
        _resolve_dict(self._groups)
        _resolve_dict(self._types)

    def register_import(self, namespace, schema):
        """Register an import for an other schema document.

        :type namespace: str
        :type schema: zeep.xsd.schema.SchemaDocument

        """
        schemas = self._imports.setdefault(namespace, [])
        schemas.append(schema)

    def is_imported(self, namespace):
        return namespace in self._imports

    def register_type(self, qname: etree.QName, value: xsd_types.Type):
        """Register a xsd.Type in this schema"""
        self._add_component(qname, value, self._types, "type")

    def register_element(self, qname: etree.QName, value: xsd_elements.Element):
        """Register a xsd.Element in this schema"""
        self._add_component(qname, value, self._elements, "element")

    def register_group(self, qname: etree.QName, value: xsd_elements.Group):
        """Register a xsd:Group in this schema"""
        self._add_component(qname, value, self._groups, "group")

    def register_attribute(self, qname: str, value: xsd_elements.Attribute):
        """Register a xsd:Attribute in this schema"""
        self._add_component(qname, value, self._attributes, "attribute")

    def register_attribute_group(
        self, qname: etree.QName, value: xsd_elements.AttributeGroup
    ) -> None:
        """Register a xsd:AttributeGroup in this schema"""
        self._add_component(qname, value, self._attribute_groups, "attribute_group")

    def get_type(self, qname: etree.QName):
        """Return a xsd.Type object from this schema

        :rtype: zeep.xsd.ComplexType or zeep.xsd.AnySimpleType

        """
        return self._get_component(qname, self._types, "type")

    def get_element(self, qname) -> xsd_elements.Element:
        """Return a xsd.Element object from this schema"""
        return self._get_component(qname, self._elements, "element")

    def get_group(self, qname) -> xsd_elements.Group:
        """Return a xsd.Group object from this schema"""
        return self._get_component(qname, self._groups, "group")

    def get_attribute(self, qname) -> xsd_elements.Attribute:
        """Return a xsd.Attribute object from this schema"""
        return self._get_component(qname, self._attributes, "attribute")

    def get_attribute_group(self, qname) -> xsd_elements.AttributeGroup:
        """Return a xsd.AttributeGroup object from this schema"""
        return self._get_component(qname, self._attribute_groups, "attributeGroup")

    def _add_component(self, name, value, items, item_name):
        if isinstance(name, etree.QName):
            name = name.text
        logger.debug("register_%s(%r, %r)", item_name, name, value)
        items[name] = value

    def _get_component(self, qname, items, item_name):
        try:
            return items[qname]
        except KeyError:
            known_items = ", ".join(items.keys())
            raise exceptions.LookupError(
                (
                    "No %(item_name)s '%(localname)s' in namespace %(namespace)s. "
                    + "Available %(item_name_plural)s are: %(known_items)s"
                )
                % {
                    "item_name": item_name,
                    "item_name_plural": item_name + "s",
                    "localname": qname.localname,
                    "namespace": qname.namespace,
                    "known_items": known_items or " - ",
                },
                qname=qname,
                item_name=item_name,
                location=self._location,
            )
