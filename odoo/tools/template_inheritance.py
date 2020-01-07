
from lxml import etree
from lxml.builder import E
import copy
import itertools

from odoo.tools.translate import _
from odoo.tools import SKIPPED_ELEMENT_TYPES


def add_text_before(node, text):
    """ Add text before ``node`` in its XML tree. """
    if text is None:
        return
    prev = node.getprevious()
    if prev is not None:
        prev.tail = (prev.tail or "") + text
    else:
        parent = node.getparent()
        parent.text = (parent.text or "") + text


def add_text_inside(node, text):
    """ Add text inside ``node``. """
    if text is None:
        return
    if len(node):
        node[-1].tail = (node[-1].tail or "") + text
    else:
        node.text = (node.text or "") + text


def remove_element(node):
    """ Remove ``node`` but not its tail, from its XML tree. """
    add_text_before(node, node.tail)
    node.tail = None
    node.getparent().remove(node)


def locate_node(arch, spec):
    """ Locate a node in a source (parent) architecture.

    Given a complete source (parent) architecture (i.e. the field
    `arch` in a view), and a 'spec' node (a node in an inheriting
    view that specifies the location in the source view of what
    should be changed), return (if it exists) the node in the
    source view matching the specification.

    :param arch: a parent architecture to modify
    :param spec: a modifying node in an inheriting view
    :return: a node in the source matching the spec
    """
    if spec.tag == 'xpath':
        nodes = etree.ETXPath(spec.get('expr'))(arch)
        return nodes[0] if nodes else None
    elif spec.tag == 'field':
        # Only compare the field name: a field can be only once in a given view
        # at a given level (and for multilevel expressions, we should use xpath
        # inheritance spec anyway).
        for node in arch.iter('field'):
            if node.get('name') == spec.get('name'):
                return node
        return None

    for node in arch.iter(spec.tag):
        if isinstance(node, SKIPPED_ELEMENT_TYPES):
            continue
        if all(node.get(attr) == spec.get(attr) for attr in spec.attrib
               if attr not in ('position', 'version')):
            # Version spec should match parent's root element's version
            if spec.get('version') and spec.get('version') != arch.get('version'):
                return None
            return node
    return None


def apply_inheritance_specs(source, specs_tree, inherit_branding=False, pre_locate=lambda s: True):
    """ Apply an inheriting view (a descendant of the base view)

    Apply to a source architecture all the spec nodes (i.e. nodes
    describing where and what changes to apply to some parent
    architecture) given by an inheriting view.

    :param Element source: a parent architecture to modify
    :param pre_locate: function that is executed before locating a node.
                        This function receives an arch as argument.
                        This is required by studio to properly handle group_ids.
    :return: a modified source where the specs are applied
    :rtype: Element
    """
    # Queue of specification nodes (i.e. nodes describing where and
    # changes to apply to some parent architecture).
    specs = specs_tree if isinstance(specs_tree, list) else [specs_tree]

    def extract(spec):
        """
        Utility function that locates a node given a specification, remove
        it from the source and returns it.
        """
        if len(spec):
            raise ValueError(
                _("Invalid specification for moved nodes: '%s'") %
                etree.tostring(spec)
            )
        pre_locate(spec)
        to_extract = locate_node(source, spec)
        if to_extract is not None:
            remove_element(to_extract)
            return to_extract
        else:
            raise ValueError(
                _("Element '%s' cannot be located in parent view") %
                etree.tostring(spec)
            )

    while len(specs):
        spec = specs.pop(0)
        if isinstance(spec, SKIPPED_ELEMENT_TYPES):
            continue
        if spec.tag == 'data':
            specs += [c for c in spec]
            continue
        pre_locate(spec)
        node = locate_node(source, spec)
        if node is not None:
            pos = spec.get('position', 'inside')
            if pos == 'replace':
                for loc in spec.xpath(".//*[text()='$0']"):
                    loc.text = ''
                    loc.append(copy.deepcopy(node))
                if node.getparent() is None:
                    spec_content = None
                    comment = None
                    for content in spec:
                        if content.tag is not etree.Comment:
                            spec_content = content
                            break
                        else:
                            comment = content
                    source = copy.deepcopy(spec_content)
                    if comment is not None:
                        text = source.text
                        source.text = None
                        comment.tail = text
                        source.insert(0, comment)
                else:
                    replaced_node_tag = None
                    for child in spec:
                        if child.get('position') == 'move':
                            child = extract(child)
                        if inherit_branding and not replaced_node_tag and child.tag is not etree.Comment:
                            # To make a correct branding, we need to
                            # - know exactly which node has been replaced
                            # - store it before anything else has altered the Tree
                            # Do it exactly here :D
                            child.set('meta-oe-xpath-replacing', node.tag)
                            # We just store the replaced node tag on the first
                            # child of the xpath replacing it
                            replaced_node_tag = node.tag
                        node.addprevious(child)
                    node.getparent().remove(node)
            elif pos == 'attributes':
                for child in spec.getiterator('attribute'):
                    attribute = child.get('name')
                    value = child.text or ''
                    if child.get('add') or child.get('remove'):
                        assert not child.text
                        separator = child.get('separator', ',')
                        if separator == ' ':
                            separator = None    # squash spaces
                        to_add = (
                            s for s in (s.strip() for s in child.get('add', '').split(separator))
                            if s
                        )
                        to_remove = {s.strip() for s in child.get('remove', '').split(separator)}
                        values = (s.strip() for s in node.get(attribute, '').split(separator))
                        value = (separator or ' ').join(itertools.chain(
                            (v for v in values if v not in to_remove),
                            to_add
                        ))
                    if value:
                        node.set(attribute, value)
                    elif attribute in node.attrib:
                        del node.attrib[attribute]
            elif pos == 'inside':
                add_text_inside(node, spec.text)
                for child in spec:
                    if child.get('position') == 'move':
                        child = extract(child)
                    node.append(child)
            elif pos == 'after':
                # add a sentinel element right after node, insert content of
                # spec before the sentinel, then remove the sentinel element
                sentinel = E.sentinel()
                node.addnext(sentinel)
                add_text_before(sentinel, spec.text)
                for child in spec:
                    if child.get('position') == 'move':
                        child = extract(child)
                    sentinel.addprevious(child)
                remove_element(sentinel)
            elif pos == 'before':
                add_text_before(node, spec.text)
                for child in spec:
                    if child.get('position') == 'move':
                        child = extract(child)
                    node.addprevious(child)
            else:
                raise ValueError(
                    _("Invalid position attribute: '%s'") %
                    pos
                )

        else:
            attrs = ''.join([
                ' %s="%s"' % (attr, spec.get(attr))
                for attr in spec.attrib
                if attr != 'position'
            ])
            tag = "<%s%s>" % (spec.tag, attrs)
            raise ValueError(
                _("Element '%s' cannot be located in parent view") % tag
            )

    return source
