import logging
import re
import typing

from lxml import etree

from zeep.exceptions import XMLParseError
from zeep.loader import absolute_location, load_external, normalize_location
from zeep.utils import as_qname, qname_attr
from zeep.xsd import elements as xsd_elements
from zeep.xsd import types as xsd_types
from zeep.xsd.const import AUTO_IMPORT_NAMESPACES, xsd_ns
from zeep.xsd.types.unresolved import UnresolvedCustomType, UnresolvedType

logger = logging.getLogger(__name__)


class tags:
    schema = xsd_ns("schema")
    import_ = xsd_ns("import")
    include = xsd_ns("include")
    annotation = xsd_ns("annotation")
    element = xsd_ns("element")
    simpleType = xsd_ns("simpleType")
    complexType = xsd_ns("complexType")
    simpleContent = xsd_ns("simpleContent")
    complexContent = xsd_ns("complexContent")
    sequence = xsd_ns("sequence")
    group = xsd_ns("group")
    choice = xsd_ns("choice")
    all = xsd_ns("all")
    list = xsd_ns("list")
    union = xsd_ns("union")
    attribute = xsd_ns("attribute")
    any = xsd_ns("any")
    anyAttribute = xsd_ns("anyAttribute")
    attributeGroup = xsd_ns("attributeGroup")
    restriction = xsd_ns("restriction")
    extension = xsd_ns("extension")
    notation = xsd_ns("notations")


class SchemaVisitor:
    """Visitor which processes XSD files and registers global elements and
    types in the given schema.

    Notes:

    TODO: include and import statements can reference other nodes. We need
    to load these first. Always global.




    :param schema:
    :type schema: zeep.xsd.schema.Schema
    :param document:
    :type document: zeep.xsd.schema.SchemaDocument

    """

    def __init__(self, schema, document):
        self.document = document
        self.schema = schema
        self._includes = set()

    def register_element(self, qname: etree.QName, instance: xsd_elements.Element):
        self.document.register_element(qname, instance)

    def register_attribute(
        self, name: etree.QName, instance: xsd_elements.Attribute
    ) -> None:
        self.document.register_attribute(name, instance)

    def register_type(self, qname: etree.QName, instance) -> None:
        self.document.register_type(qname, instance)

    def register_group(self, qname: etree.QName, instance: xsd_elements.Group):
        self.document.register_group(qname, instance)

    def register_attribute_group(
        self, qname: etree.QName, instance: xsd_elements.AttributeGroup
    ) -> None:
        self.document.register_attribute_group(qname, instance)

    def register_import(self, namespace, document):
        self.document.register_import(namespace, document)

    def process(self, node, parent):
        visit_func = self.visitors.get(node.tag)
        if not visit_func:
            raise ValueError("No visitor defined for %r" % node.tag)
        result = visit_func(self, node, parent)
        return result

    def process_ref_attribute(self, node, array_type=None):
        ref = qname_attr(node, "ref")
        if ref:
            ref = self._create_qname(ref)

            # Some wsdl's reference to xs:schema, we ignore that for now. It
            # might be better in the future to process the actual schema file
            # so that it is handled correctly
            if ref.namespace == "http://www.w3.org/2001/XMLSchema":
                return
            return xsd_elements.RefAttribute(
                node.tag, ref, self.schema, array_type=array_type
            )

    def process_reference(self, node, **kwargs):
        ref = qname_attr(node, "ref")
        if not ref:
            return

        ref = self._create_qname(ref)

        if node.tag == tags.element:
            cls = xsd_elements.RefElement
        elif node.tag == tags.attribute:
            cls = xsd_elements.RefAttribute
        elif node.tag == tags.group:
            cls = xsd_elements.RefGroup
        elif node.tag == tags.attributeGroup:
            cls = xsd_elements.RefAttributeGroup
        return cls(node.tag, ref, self.schema, **kwargs)

    def visit_schema(self, node):
        """Visit the xsd:schema element and process all the child elements

        Definition::

            <schema
              attributeFormDefault = (qualified | unqualified): unqualified
              blockDefault = (#all | List of (extension | restriction | substitution) : ''
              elementFormDefault = (qualified | unqualified): unqualified
              finalDefault = (#all | List of (extension | restriction | list | union): ''
              id = ID
              targetNamespace = anyURI
              version = token
              xml:lang = language
              {any attributes with non-schema Namespace}...>
            Content: (
                (include | import | redefine | annotation)*,
                (((simpleType | complexType | group | attributeGroup) |
                  element | attribute | notation),
                 annotation*)*)
            </schema>

        :param node: The XML node
        :type node: lxml.etree._Element

        """
        assert node is not None

        # A schema should always have a targetNamespace attribute, otherwise
        # it is called a chameleon schema. In that case the schema will inherit
        # the namespace of the enclosing schema/node.
        tns = node.get("targetNamespace")
        if tns:
            self.document._target_namespace = tns
        self.document._element_form = node.get("elementFormDefault", "unqualified")
        self.document._attribute_form = node.get("attributeFormDefault", "unqualified")

        for child in node:
            self.process(child, parent=node)

    def visit_import(self, node, parent):
        """

        Definition::

            <import
              id = ID
              namespace = anyURI
              schemaLocation = anyURI
              {any attributes with non-schema Namespace}...>
            Content: (annotation?)
            </import>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        schema_node = None
        namespace = node.get("namespace")
        location = node.get("schemaLocation")
        if location:
            location = normalize_location(
                self.schema.settings, location, self.document._base_url
            )

        if not namespace and not self.document._target_namespace:
            raise XMLParseError(
                "The attribute 'namespace' must be existent if the "
                "importing schema has no target namespace.",
                filename=self.document.location,
                sourceline=node.sourceline,
            )

        # We found an empty <import/> statement, this needs to trigger 4.1.2
        # from https://www.w3.org/TR/2012/REC-xmlschema11-1-20120405/#src-resolve
        # for QName resolving.
        # In essence this means we will resolve QNames without a namespace to no
        # namespace instead of the target namespace.
        # The following code snippet works because imports have to occur before we
        # visit elements.
        if not namespace and not location:
            self.document._has_empty_import = True

        # Check if the schema is already imported before based on the
        # namespace. Schema's without namespace are registered as 'None'
        document = self.schema.documents.get_by_namespace_and_location(
            namespace, location
        )
        if document:
            logger.debug("Returning existing schema: %r", location)
            self.register_import(namespace, document)
            return document

        # Hardcode the mapping between the xml namespace and the xsd for now.
        # This seems to fix issues with exchange wsdl's, see #220
        if not location and namespace == "http://www.w3.org/XML/1998/namespace":
            location = "https://www.w3.org/2001/xml.xsd"

        # Silently ignore import statements which we can't resolve via the
        # namespace and doesn't have a schemaLocation attribute.
        if not location:
            logger.debug(
                "Ignoring import statement for namespace %r "
                + "(missing schemaLocation)",
                namespace,
            )
            return

        # Load the XML
        schema_node = self._retrieve_data(location, base_url=self.document._location)

        # Check if the xsd:import namespace matches the targetNamespace. If
        # the xsd:import statement didn't specify a namespace then make sure
        # that the targetNamespace wasn't declared by another schema yet.
        schema_tns = schema_node.get("targetNamespace")
        if namespace and schema_tns and namespace != schema_tns:
            raise XMLParseError(
                (
                    "The namespace defined on the xsd:import doesn't match the "
                    "imported targetNamespace located at %r "
                )
                % (location),
                filename=self.document._location,
                sourceline=node.sourceline,
            )

        # If the imported schema doesn't define a target namespace and the
        # node doesn't specify it either then inherit the existing target
        # namespace.
        elif not schema_tns and not namespace:
            namespace = self.document._target_namespace

        schema = self.schema.create_new_document(
            schema_node, location, target_namespace=namespace
        )
        self.register_import(namespace, schema)
        return schema

    def visit_include(self, node, parent):
        """

        Definition::

            <include
              id = ID
              schemaLocation = anyURI
              {any attributes with non-schema Namespace}...>
            Content: (annotation?)
            </include>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        if not node.get("schemaLocation"):
            raise NotImplementedError("schemaLocation is required")
        location = node.get("schemaLocation")

        if location in self._includes:
            return

        schema_node = self._retrieve_data(location, base_url=self.document._base_url)
        self._includes.add(location)

        # When the included document has no default namespace defined but the
        # parent document does have this then we should (atleast for #360)
        # transfer the default namespace to the included schema. We can't
        # update the nsmap of elements in lxml so we create a new schema with
        # the correct nsmap and move all the content there.

        # Included schemas must have targetNamespace equal to parent schema (the including) or None.
        # If included schema doesn't have default ns, then it should be set to parent's targetNs.
        # See Chameleon Inclusion https://www.w3.org/TR/xmlschema11-1/#chameleon-xslt
        if not schema_node.nsmap.get(None) and (
            node.nsmap.get(None) or parent.attrib.get("targetNamespace")
        ):
            nsmap = {None: node.nsmap.get(None) or parent.attrib["targetNamespace"]}
            nsmap.update(schema_node.nsmap)
            new = etree.Element(schema_node.tag, nsmap=nsmap)
            for child in schema_node:
                new.append(child)
            for key, value in schema_node.attrib.items():
                new.set(key, value)
            if not new.attrib.get("targetNamespace"):
                new.attrib["targetNamespace"] = parent.attrib["targetNamespace"]
            schema_node = new

        # Use the element/attribute form defaults from the schema while
        # processing the nodes.
        element_form_default = self.document._element_form
        attribute_form_default = self.document._attribute_form
        base_url = self.document._base_url

        self.document._element_form = schema_node.get(
            "elementFormDefault", "unqualified"
        )
        self.document._attribute_form = schema_node.get(
            "attributeFormDefault", "unqualified"
        )
        self.document._base_url = absolute_location(location, self.document._base_url)

        # Iterate directly over the children.
        for child in schema_node:
            self.process(child, parent=schema_node)

        self.document._element_form = element_form_default
        self.document._attribute_form = attribute_form_default
        self.document._base_url = base_url

    def visit_element(self, node, parent):
        """

        Definition::

            <element
              abstract = Boolean : false
              block = (#all | List of (extension | restriction | substitution))
              default = string
              final = (#all | List of (extension | restriction))
              fixed = string
              form = (qualified | unqualified)
              id = ID
              maxOccurs = (nonNegativeInteger | unbounded) : 1
              minOccurs = nonNegativeInteger : 1
              name = NCName
              nillable = Boolean : false
              ref = QName
              substitutionGroup = QName
              type = QName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (
                      (simpleType | complexType)?, (unique | key | keyref)*))
            </element>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        is_global = parent.tag == tags.schema

        # minOccurs / maxOccurs are not allowed on global elements
        if not is_global:
            min_occurs, max_occurs = _process_occurs_attrs(node)
        else:
            max_occurs = 1
            min_occurs = 1

        # If the element has a ref attribute then all other attributes cannot
        # be present. Short circuit that here.
        # Ref is prohibited on global elements (parent = schema)
        if not is_global:
            # Naive workaround to mark fields which are part of a choice element
            # as optional
            if parent.tag == tags.choice:
                min_occurs = 0
            result = self.process_reference(
                node, min_occurs=min_occurs, max_occurs=max_occurs
            )
            if result:
                return result

        element_form = node.get("form", self.document._element_form)
        if element_form == "qualified" or is_global:
            qname = qname_attr(node, "name", self.document._target_namespace)
        else:
            qname = etree.QName(node.get("name").strip())

        children = list(node)
        xsd_type = None
        if children:
            value = None

            for child in children:
                if child.tag == tags.annotation:
                    continue

                elif child.tag in (tags.simpleType, tags.complexType):
                    assert not value

                    xsd_type = self.process(child, node)

        if not xsd_type:
            node_type = qname_attr(node, "type")
            if node_type:
                xsd_type = self._get_type(node_type.text)
            else:
                xsd_type = xsd_types.AnyType()

        nillable = node.get("nillable") == "true"
        default = node.get("default")
        element = xsd_elements.Element(
            name=qname,
            type_=xsd_type,
            min_occurs=min_occurs,
            max_occurs=max_occurs,
            nillable=nillable,
            default=default,
            is_global=is_global,
        )

        # Only register global elements
        if is_global:
            self.register_element(qname, element)
        return element

    def visit_attribute(
        self, node: etree._Element, parent: etree._Element
    ) -> typing.Union[xsd_elements.Attribute, xsd_elements.RefAttribute]:
        """Declares an attribute.

        Definition::

            <attribute
              default = string
              fixed = string
              form = (qualified | unqualified)
              id = ID
              name = NCName
              ref = QName
              type = QName
              use = (optional | prohibited | required): optional
              {any attributes with non-schema Namespace...}>
            Content: (annotation?, (simpleType?))
            </attribute>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        is_global = parent.tag == tags.schema

        # Check of wsdl:arayType
        array_type = node.get("{http://schemas.xmlsoap.org/wsdl/}arrayType")
        if array_type:
            match = re.match(r"([^\[]+)", array_type)
            if match:
                array_type = match.groups()[0]
                qname = as_qname(array_type, node.nsmap)
                array_type = UnresolvedType(qname, self.schema)

        # If the elment has a ref attribute then all other attributes cannot
        # be present. Short circuit that here.
        # Ref is prohibited on global elements (parent = schema)
        if not is_global:
            result = self.process_ref_attribute(node, array_type=array_type)
            if result:
                return result

        attribute_form = node.get("form", self.document._attribute_form)
        if attribute_form == "qualified" or is_global:
            name = qname_attr(node, "name", self.document._target_namespace)
        else:
            name = etree.QName(node.get("name"))

        annotation, items = self._pop_annotation(list(node))
        if items:
            xsd_type = self.visit_simple_type(items[0], node)
        else:
            node_type = qname_attr(node, "type")
            if node_type:
                xsd_type = self._get_type(node_type)
            else:
                xsd_type = xsd_types.AnyType()

        # TODO: We ignore 'prohobited' for now
        required = node.get("use") == "required"
        default = node.get("default")

        attr = xsd_elements.Attribute(
            name, type_=xsd_type, default=default, required=required
        )

        # Only register global elements
        if is_global:
            assert name is not None
            self.register_attribute(name, attr)
        return attr

    def visit_simple_type(self, node, parent):
        """
        Definition::

            <simpleType
              final = (#all | (list | union | restriction))
              id = ID
              name = NCName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (restriction | list | union))
            </simpleType>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """

        if parent.tag == tags.schema:
            name = node.get("name")
            is_global = True
        else:
            name = parent.get("name", "Anonymous")
            is_global = False
        base_type = "{http://www.w3.org/2001/XMLSchema}string"
        qname = as_qname(name, node.nsmap, self.document._target_namespace)

        annotation, items = self._pop_annotation(list(node))
        child = items[0]
        if child.tag == tags.restriction:
            base_type = self.visit_restriction_simple_type(child, node)
            xsd_type = UnresolvedCustomType(qname, base_type, self.schema)

        elif child.tag == tags.list:
            xsd_type = self.visit_list(child, node)

        elif child.tag == tags.union:
            xsd_type = self.visit_union(child, node)
        else:
            raise AssertionError("Unexpected child: %r" % child.tag)

        assert xsd_type is not None
        if is_global:
            self.register_type(qname, xsd_type)
        return xsd_type

    def visit_complex_type(self, node, parent):
        """
        Definition::

            <complexType
              abstract = Boolean : false
              block = (#all | List of (extension | restriction))
              final = (#all | List of (extension | restriction))
              id = ID
              mixed = Boolean : false
              name = NCName
              {any attributes with non-schema Namespace...}>
            Content: (annotation?, (simpleContent | complexContent |
                      ((group | all | choice | sequence)?,
                      ((attribute | attributeGroup)*, anyAttribute?))))
            </complexType>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        children = []
        base_type = "{http://www.w3.org/2001/XMLSchema}anyType"

        # If the complexType's parent is an element then this type is
        # anonymous and should have no name defined. Otherwise it's global
        if parent.tag == tags.schema:
            name = node.get("name")
            is_global = True
        else:
            name = parent.get("name")
            is_global = False

        qname = as_qname(name, node.nsmap, self.document._target_namespace)
        cls_attributes = {"__module__": "zeep.xsd.dynamic_types", "_xsd_name": qname}
        xsd_cls = type(name, (xsd_types.ComplexType,), cls_attributes)
        xsd_type = None

        # Process content
        annotation, children = self._pop_annotation(list(node))
        first_tag = children[0].tag if children else None

        if first_tag == tags.simpleContent:
            base_type, attributes = self.visit_simple_content(children[0], node)

            xsd_type = xsd_cls(
                attributes=attributes,
                extension=base_type,
                qname=qname,
                is_global=is_global,
            )

        elif first_tag == tags.complexContent:
            kwargs = self.visit_complex_content(children[0], node)
            xsd_type = xsd_cls(qname=qname, is_global=is_global, **kwargs)

        elif first_tag:
            element = None

            if first_tag in (tags.group, tags.all, tags.choice, tags.sequence):
                child = children.pop(0)
                element = self.process(child, node)

            attributes = self._process_attributes(node, children)
            xsd_type = xsd_cls(
                element=element, attributes=attributes, qname=qname, is_global=is_global
            )
        else:
            xsd_type = xsd_cls(qname=qname, is_global=is_global)

        if is_global:
            self.register_type(qname, xsd_type)
        return xsd_type

    def visit_complex_content(self, node, parent):
        """The complexContent element defines extensions or restrictions on a
        complex type that contains mixed content or elements only.

        Definition::

            <complexContent
              id = ID
              mixed = Boolean
              {any attributes with non-schema Namespace}...>
            Content: (annotation?,  (restriction | extension))
            </complexContent>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        children = list(node)
        child = children[-1]

        if child.tag == tags.restriction:
            base, element, attributes = self.visit_restriction_complex_content(
                child, node
            )
            return {"attributes": attributes, "element": element, "restriction": base}
        elif child.tag == tags.extension:
            base, element, attributes = self.visit_extension_complex_content(
                child, node
            )
            return {"attributes": attributes, "element": element, "extension": base}

    def visit_simple_content(self, node, parent):
        """Contains extensions or restrictions on a complexType element with
        character data or a simpleType element as content and contains no
        elements.

        Definition::

            <simpleContent
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (restriction | extension))
            </simpleContent>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """

        children = list(node)
        child = children[-1]

        if child.tag == tags.restriction:
            return self.visit_restriction_simple_content(child, node)
        elif child.tag == tags.extension:
            return self.visit_extension_simple_content(child, node)
        raise AssertionError("Expected restriction or extension")

    def visit_restriction_simple_type(self, node, parent):
        """
        Definition::

            <restriction
              base = QName
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (annotation?,
                (simpleType?, (
                    minExclusive | minInclusive | maxExclusive | maxInclusive |
                    totalDigits |fractionDigits | length | minLength |
                    maxLength | enumeration | whiteSpace | pattern)*))
            </restriction>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        base_name = qname_attr(node, "base")
        if base_name:
            return self._get_type(base_name)

        annotation, children = self._pop_annotation(list(node))
        if children[0].tag == tags.simpleType:
            return self.visit_simple_type(children[0], node)

    def visit_restriction_simple_content(self, node, parent):
        """
        Definition::

            <restriction
              base = QName
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (annotation?,
                (simpleType?, (
                    minExclusive | minInclusive | maxExclusive | maxInclusive |
                    totalDigits |fractionDigits | length | minLength |
                    maxLength | enumeration | whiteSpace | pattern)*
                )?, ((attribute | attributeGroup)*, anyAttribute?))
            </restriction>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        base_name = qname_attr(node, "base")
        base_type = self._get_type(base_name)
        return base_type, []

    def visit_restriction_complex_content(self, node, parent):
        """

        Definition::

            <restriction
              base = QName
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (group | all | choice | sequence)?,
                    ((attribute | attributeGroup)*, anyAttribute?))
            </restriction>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        base_name = qname_attr(node, "base")
        base_type = self._get_type(base_name)
        annotation, children = self._pop_annotation(list(node))

        element = None
        attributes = []

        if children:
            child = children[0]
            if child.tag in (tags.group, tags.all, tags.choice, tags.sequence):
                children.pop(0)
                element = self.process(child, node)
            attributes = self._process_attributes(node, children)
        return base_type, element, attributes

    def visit_extension_complex_content(self, node, parent):
        """

        Definition::

            <extension
              base = QName
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (
                        (group | all | choice | sequence)?,
                        ((attribute | attributeGroup)*, anyAttribute?)))
            </extension>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        base_name = qname_attr(node, "base")
        base_type = self._get_type(base_name)
        annotation, children = self._pop_annotation(list(node))

        element = None
        attributes = []

        if children:
            child = children[0]
            if child.tag in (tags.group, tags.all, tags.choice, tags.sequence):
                children.pop(0)
                element = self.process(child, node)
            attributes = self._process_attributes(node, children)

        return base_type, element, attributes

    def visit_extension_simple_content(self, node, parent):
        """

        Definition::

            <extension
              base = QName
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, ((attribute | attributeGroup)*, anyAttribute?))
            </extension>
        """
        base_name = qname_attr(node, "base")
        base_type = self._get_type(base_name)
        annotation, children = self._pop_annotation(list(node))
        attributes = self._process_attributes(node, children)

        return base_type, attributes

    def visit_annotation(self, node, parent):
        """Defines an annotation.

        Definition::

            <annotation
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (appinfo | documentation)*
            </annotation>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        return

    def visit_any(self, node, parent):
        """

        Definition::

            <any
              id = ID
              maxOccurs = (nonNegativeInteger | unbounded) : 1
              minOccurs = nonNegativeInteger : 1
              namespace = "(##any | ##other) |
                List of (anyURI | (##targetNamespace |  ##local))) : ##any
              processContents = (lax | skip | strict) : strict
              {any attributes with non-schema Namespace...}>
            Content: (annotation?)
            </any>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        min_occurs, max_occurs = _process_occurs_attrs(node)
        process_contents = node.get("processContents", "strict")
        return xsd_elements.Any(
            max_occurs=max_occurs,
            min_occurs=min_occurs,
            process_contents=process_contents,
        )

    def visit_sequence(self, node, parent):
        """
        Definition::

            <sequence
              id = ID
              maxOccurs = (nonNegativeInteger | unbounded) : 1
              minOccurs = nonNegativeInteger : 1
              {any attributes with non-schema Namespace}...>
            Content: (annotation?,
                      (element | group | choice | sequence | any)*)
            </sequence>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """

        sub_types = [
            tags.annotation,
            tags.any,
            tags.choice,
            tags.element,
            tags.group,
            tags.sequence,
        ]
        min_occurs, max_occurs = _process_occurs_attrs(node)
        result = xsd_elements.Sequence(min_occurs=min_occurs, max_occurs=max_occurs)

        annotation, children = self._pop_annotation(list(node))
        for child in children:
            if child.tag not in sub_types:
                raise self._create_error(
                    "Unexpected element %s in xsd:sequence" % child.tag, child
                )

            item = self.process(child, node)
            assert item is not None
            result.append(item)

        assert None not in result
        return result

    def visit_all(self, node, parent):
        """Allows the elements in the group to appear (or not appear) in any
        order in the containing element.

        Definition::

            <all
              id = ID
              maxOccurs= 1: 1
              minOccurs= (0 | 1): 1
              {any attributes with non-schema Namespace...}>
            Content: (annotation?, element*)
            </all>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """

        sub_types = [tags.annotation, tags.element]
        result = xsd_elements.All()

        annotation, children = self._pop_annotation(list(node))
        for child in children:
            assert child.tag in sub_types, child
            item = self.process(child, node)
            result.append(item)

        assert None not in result
        return result

    def visit_group(self, node, parent):
        """Groups a set of element declarations so that they can be
        incorporated as a group into complex type definitions.

        Definition::

            <group
              name= NCName
              id = ID
              maxOccurs = (nonNegativeInteger | unbounded) : 1
              minOccurs = nonNegativeInteger : 1
              name = NCName
              ref = QName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (all | choice | sequence))
            </group>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        min_occurs, max_occurs = _process_occurs_attrs(node)

        result = self.process_reference(
            node, min_occurs=min_occurs, max_occurs=max_occurs
        )
        if result:
            return result

        qname = qname_attr(node, "name", self.document._target_namespace)

        # There should be only max nodes, first node (annotation) is irrelevant
        annotation, children = self._pop_annotation(list(node))
        child = children[0]

        item = self.process(child, parent)
        elm = xsd_elements.Group(name=qname, child=item)

        if parent.tag == tags.schema:
            self.register_group(qname, elm)
        return elm

    def visit_list(self, node, parent):
        """
        Definition::

            <list
              id = ID
              itemType = QName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (simpleType?))
            </list>

        The use of the simpleType element child and the itemType attribute is
        mutually exclusive.

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element


        """
        item_type = qname_attr(node, "itemType")
        if item_type:
            sub_type = self._get_type(item_type.text)
        else:
            subnodes = list(node)
            child = subnodes[-1]  # skip annotation
            sub_type = self.visit_simple_type(child, node)
        return xsd_types.ListType(sub_type)

    def visit_choice(self, node, parent):
        """
        Definition::

            <choice
              id = ID
              maxOccurs= (nonNegativeInteger | unbounded) : 1
              minOccurs= nonNegativeInteger : 1
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (element | group | choice | sequence | any)*)
            </choice>
        """
        min_occurs, max_occurs = _process_occurs_attrs(node)

        annotation, children = self._pop_annotation(list(node))

        choices = []
        for child in children:
            elm = self.process(child, node)
            choices.append(elm)
        return xsd_elements.Choice(
            choices, min_occurs=min_occurs, max_occurs=max_occurs
        )

    def visit_union(self, node, parent):
        """Defines a collection of multiple simpleType definitions.

        Definition::

            <union
              id = ID
              memberTypes = List of QNames
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (simpleType*))
            </union>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        # TODO
        members = node.get("memberTypes")
        types = []
        if members:
            for member in members.split():
                qname = as_qname(member, node.nsmap)
                xsd_type = self._get_type(qname)
                types.append(xsd_type)
        else:
            annotation, types = self._pop_annotation(list(node))
            types = [self.visit_simple_type(t, node) for t in types]
        return xsd_types.UnionType(types)

    def visit_unique(self, node, parent):
        """Specifies that an attribute or element value (or a combination of
        attribute or element values) must be unique within the specified scope.
        The value must be unique or nil.

        Definition::

            <unique
              id = ID
              name = NCName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (selector, field+))
            </unique>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        # TODO
        pass

    def visit_attribute_group(self, node, parent):
        """
        Definition::

            <attributeGroup
              id = ID
              name = NCName
              ref = QName
              {any attributes with non-schema Namespace...}>
            Content: (annotation?),
                     ((attribute | attributeGroup)*, anyAttribute?))
            </attributeGroup>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        ref = self.process_reference(node)
        if ref:
            return ref

        qname = qname_attr(node, "name", self.document._target_namespace)
        annotation, children = self._pop_annotation(list(node))

        attributes = self._process_attributes(node, children)
        attribute_group = xsd_elements.AttributeGroup(qname, attributes)
        self.register_attribute_group(qname, attribute_group)

    def visit_any_attribute(self, node, parent):
        """
        Definition::

            <anyAttribute
              id = ID
              namespace = ((##any | ##other) |
                List of (anyURI | (##targetNamespace | ##local))) : ##any
              processContents = (lax | skip | strict): strict
              {any attributes with non-schema Namespace...}>
            Content: (annotation?)
            </anyAttribute>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        process_contents = node.get("processContents", "strict")
        return xsd_elements.AnyAttribute(process_contents=process_contents)

    def visit_notation(self, node, parent):
        """Contains the definition of a notation to describe the format of
        non-XML data within an XML document. An XML Schema notation declaration
        is a reconstruction of XML 1.0 NOTATION declarations.

        Definition::

            <notation
              id = ID
              name = NCName
              public = Public identifier per ISO 8879
              system = anyURI
              {any attributes with non-schema Namespace}...>
            Content: (annotation?)
            </notation>

        :param node: The XML node
        :type node: lxml.etree._Element
        :param parent: The parent XML node
        :type parent: lxml.etree._Element

        """
        pass

    def _retrieve_data(self, url: typing.IO, base_url=None):
        return load_external(
            url, self.schema._transport, base_url, settings=self.schema.settings
        )

    def _get_type(self, name):
        assert name is not None
        name = self._create_qname(name)
        return UnresolvedType(name, self.schema)

    def _create_qname(self, name):
        if not isinstance(name, etree.QName):
            name = etree.QName(name)

        # Handle reserved namespace
        if name.namespace == "xml":
            name = etree.QName("http://www.w3.org/XML/1998/namespace", name.localname)

        # Various xsd builders assume that some schema's are available by
        # default (actually this is mostly just the soap-enc ns). So live with
        # that fact and handle it by auto-importing the schema if it is
        # referenced.
        if name.namespace in AUTO_IMPORT_NAMESPACES and not self.document.is_imported(
            name.namespace
        ):
            logger.debug("Auto importing missing known schema: %s", name.namespace)
            import_node = etree.Element(
                tags.import_, namespace=name.namespace, schemaLocation=name.namespace
            )
            self.visit_import(import_node, None)

        if (
            not name.namespace
            and self.document._element_form == "qualified"
            and self.document._target_namespace
            and not self.document._has_empty_import
        ):
            name = etree.QName(self.document._target_namespace, name.localname)
        return name

    def _pop_annotation(self, items):
        if not len(items):
            return None, []

        if items[0].tag == tags.annotation:
            annotation = self.visit_annotation(items[0], None)
            return annotation, items[1:]
        return None, items

    def _process_attributes(self, node, items):
        attributes = []
        for child in items:
            if child.tag in (tags.attribute, tags.attributeGroup, tags.anyAttribute):
                attribute = self.process(child, node)
                attributes.append(attribute)
            else:
                raise self._create_error("Unexpected tag `%s`" % (child.tag), node)
        return attributes

    def _create_error(self, message, node):
        return XMLParseError(
            message, filename=self.document._location, sourceline=node.sourceline
        )

    visitors = {
        tags.any: visit_any,
        tags.element: visit_element,
        tags.choice: visit_choice,
        tags.simpleType: visit_simple_type,
        tags.anyAttribute: visit_any_attribute,
        tags.complexType: visit_complex_type,
        tags.simpleContent: None,
        tags.complexContent: None,
        tags.sequence: visit_sequence,
        tags.all: visit_all,
        tags.group: visit_group,
        tags.attribute: visit_attribute,
        tags.import_: visit_import,
        tags.include: visit_include,
        tags.annotation: visit_annotation,
        tags.attributeGroup: visit_attribute_group,
        tags.notation: visit_notation,
    }


def _process_occurs_attrs(node):
    """Process the min/max occurrence indicators"""
    max_occurs = node.get("maxOccurs", "1")
    min_occurs = int(node.get("minOccurs", "1"))
    if max_occurs == "unbounded":
        max_occurs = "unbounded"
    else:
        max_occurs = int(max_occurs)

    return min_occurs, max_occurs
