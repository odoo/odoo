import re

from lxml import etree


def process_multiref(node):
    """Iterate through the tree and replace the referened elements.

    This method replaces the nodes with an href attribute and replaces it
    with the elements it's referencing to (which have an id attribute).abs

    """
    multiref_objects = {elm.attrib["id"]: elm for elm in node.xpath("*[@id]")}
    if not multiref_objects:
        return

    used_nodes = []

    def process(node):
        """Recursive"""
        # TODO (In Soap 1.2 this is 'ref')
        href = node.attrib.get("href")

        if href and href.startswith("#"):
            obj = multiref_objects.get(href[1:])
            if obj is not None:
                used_nodes.append(obj)
                node = _dereference_element(obj, node)

        for child in node:
            process(child)

    process(node)

    # Remove the old dereferenced nodes from the tree
    for node in used_nodes:
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)


def _dereference_element(source, target):
    """Move the referenced node (source) in the main response tree (target)

    :type source: lxml.etree._Element
    :type target: lxml.etree._Element
    :rtype target: lxml.etree._Element

    """
    specific_nsmap = {k: v for k, v in source.nsmap.items() if k not in target.nsmap}

    new = _clone_element(source, target.tag, specific_nsmap)

    # Replace the node with the new dereferenced node
    parent = target.getparent()
    parent.insert(parent.index(target), new)
    parent.remove(target)

    # Update all descendants
    for obj in new.iter():
        _prefix_node(obj)

    return new


def _clone_element(node, tag_name=None, nsmap=None):
    """Clone the given node and return it.

    This is a recursive call since we want to clone the children the same
    way.

    :type source: lxml.etree._Element
    :type tag_name: str
    :type nsmap: dict
    :rtype source: lxml.etree._Element

    """
    tag_name = tag_name or node.tag
    nsmap = node.nsmap if nsmap is None else nsmap
    new = etree.Element(tag_name, nsmap=nsmap)

    for child in node:
        new_child = _clone_element(child)
        new.append(new_child)
    new.text = node.text

    for key, value in _get_attributes(node):
        new.set(key, value)

    return new


def _prefix_node(node):
    """Translate the internal attribute values back to prefixed tokens.

    This reverses the translation done in _get_attributes

    For example::

        {
            'foo:type': '{http://example.com}string'
        }

    will be converted to:

        {
            'foo:type': 'example:string'
        }

    :type node: lxml.etree._Element

    """
    reverse_nsmap = {v: k for k, v in node.nsmap.items()}

    prefix_re = re.compile("^{([^}]+)}(.*)")

    for key, value in node.attrib.items():
        if value.startswith("{"):
            match = prefix_re.match(value)
            if not match:
                continue
            namespace, localname = match.groups()

            if namespace in reverse_nsmap:
                value = "%s:%s" % (reverse_nsmap.get(namespace), localname)
                node.set(key, value)


def _get_attributes(node):
    """Return the node attributes where prefixed values are dereferenced.

    For example the following xml::

        <foobar xmlns:xsi="foo" xmlns:ns0="bar" xsi:type="ns0:string">

    will return the dict::

        {
            'foo:type': '{http://example.com}string'
        }

    :type node: lxml.etree._Element

    """
    nsmap = node.nsmap
    result = {}

    for key, value in node.attrib.items():
        if value.count(":") == 1:
            prefix, localname = value.split(":")

            if prefix in nsmap:
                namespace = nsmap[prefix]
                value = "{%s}%s" % (namespace, localname)
        result[key] = value
    return list(result.items())
