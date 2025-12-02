import copy
import itertools
import logging
import re

from lxml import etree
from lxml.builder import E

from odoo.tools.translate import LazyTranslate
from odoo.exceptions import ValidationError
from .misc import SKIPPED_ELEMENT_TYPES, html_escape

__all__ = []

_lt = LazyTranslate('base')
_logger = logging.getLogger(__name__)
RSTRIP_REGEXP = re.compile(r'\n[ \t]*$')

# attribute names that contain Python expressions
PYTHON_ATTRIBUTES = {'readonly', 'required', 'invisible', 'column_invisible', 't-if', 't-elif'}


def add_stripped_items_before(node, spec, extract):
    text = spec.text or ''

    before_text = ''
    prev = next((n for n in node.itersiblings(preceding=True) if not (n.tag == etree.ProcessingInstruction and n.target == "apply-inheritance-specs-node-removal")), None)
    if prev is None:
        parent = node.getparent()
        result = parent.text and RSTRIP_REGEXP.search(parent.text)
        before_text = result.group(0) if result else ''
        fallback_text = None if spec.text is None else ''
        parent.text = ((parent.text or '').rstrip() + text) or fallback_text
    else:
        result = prev.tail and RSTRIP_REGEXP.search(prev.tail)
        before_text = result.group(0) if result else ''
        prev.tail = (prev.tail or '').rstrip() + text

    if len(spec) > 0:
        spec[-1].tail = (spec[-1].tail or "").rstrip() + before_text
    else:
        spec.text = (spec.text or "").rstrip() + before_text

    for child in spec:
        if child.get('position') == 'move':
            tail = child.tail
            child = extract(child)
            child.tail = tail
        node.addprevious(child)


def add_text_before(node, text):
    """ Add text before ``node`` in its XML tree. """
    if text is None:
        return
    prev = node.getprevious()
    if prev is not None:
        prev.tail = (prev.tail or "") + text
    else:
        parent = node.getparent()
        parent.text = (parent.text or "").rstrip() + text


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
        expr = spec.get('expr')
        try:
            xPath = etree.ETXPath(expr)
        except etree.XPathSyntaxError as e:
            raise ValidationError(_lt("Invalid Expression while parsing xpath “%s”", expr)) from e
        nodes = xPath(arch)
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
        if all(node.get(attr) == spec.get(attr) for attr in spec.attrib if attr != 'position'):
            return node
    return None


def apply_inheritance_specs(source, specs_tree, inherit_branding=False, pre_locate=None):
    """ Apply an inheriting view (a descendant of the base view)

    Apply to a source architecture all the spec nodes (i.e. nodes
    describing where and what changes to apply to some parent
    architecture) given by an inheriting view.

    :param Element source: a parent architecture to modify
    :param Element specs_tree: a modifying architecture in an inheriting view
    :param bool inherit_branding:
    :param pre_locate: function that is executed before locating a node.
                        This function receives an arch as argument.
                        This is required by studio to properly handle group_ids.
    :return: a modified source where the specs are applied
    :rtype: Element
    """
    # Queue of specification nodes (i.e. nodes describing where and
    # changes to apply to some parent architecture).
    specs = specs_tree if isinstance(specs_tree, list) else [specs_tree]
    pre_locate = pre_locate or (lambda _: True)

    def extract(spec):
        """
        Utility function that locates a node given a specification, remove
        it from the source and returns it.
        """
        if len(spec):
            raise ValueError(
                _lt("Invalid specification for moved nodes: “%s”", etree.tostring(spec, encoding='unicode'))
            )
        pre_locate(spec)
        to_extract = locate_node(source, spec)
        if to_extract is not None:
            remove_element(to_extract)
            return to_extract
        else:
            raise ValueError(
                _lt("Element “%s” cannot be located in parent view", etree.tostring(spec, encoding='unicode'))
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
                mode = spec.get('mode', 'outer')
                if mode == "outer":
                    for loc in spec.xpath(".//*[text()='$0']"):
                        loc.text = ''
                        copied_node = copy.deepcopy(node)
                        # TODO: Remove 'inherit_branding' logic if possible;
                        # currently needed to track node removal for branding
                        # distribution. Avoid marking root nodes to prevent
                        # sibling branding issues.
                        if inherit_branding:
                            copied_node.set('data-oe-no-branding', '1')
                        loc.append(copied_node)
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
                        # only keep the t-name of a template root node
                        t_name = node.get('t-name')
                        if t_name:
                            source.set('t-name', t_name)
                        if comment is not None:
                            text = source.text
                            source.text = None
                            comment.tail = text
                            source.insert(0, comment)
                    else:
                        # TODO ideally the notion of 'inherit_branding' should
                        # not exist in this function. Given the current state of
                        # the code, it is however necessary to know where nodes
                        # were removed when distributing branding. As a stable
                        # fix, this solution was chosen: the location is marked
                        # with a "ProcessingInstruction" which will not impact
                        # the "Element" structure of the resulting tree.
                        # Exception: if we happen to replace a node that already
                        # has xpath branding (root level nodes), do not mark the
                        # location of the removal as it will mess up the branding
                        # of siblings elements coming from other views, after the
                        # branding is distributed (and those processing instructions
                        # removed).
                        if inherit_branding and not node.get('data-oe-xpath'):
                            node.addprevious(etree.ProcessingInstruction('apply-inheritance-specs-node-removal', node.tag))

                        for child in spec:
                            if child.get('position') == 'move':
                                child = extract(child)
                            node.addprevious(child)
                        node.getparent().remove(node)
                elif mode == "inner":
                    # use a sentinel to keep the existing children nodes, so
                    # that one can move existing children nodes inside the new
                    # content of the node (with position="move")
                    sentinel = E.sentinel()
                    if len(node) > 0:
                        node[0].addprevious(sentinel)
                    else:
                        node.append(sentinel)
                    # fill the node with the spec *before* the sentinel
                    # remove node.text before that operation, otherwise it will
                    # be merged with the new content's text
                    node.text = None
                    add_stripped_items_before(sentinel, copy.deepcopy(spec), extract)
                    # now remove the old content and the sentinel
                    for child in reversed(node):
                        node.remove(child)
                        if child == sentinel:
                            break
                else:
                    raise ValueError(_lt("Invalid mode attribute: “%s”", mode))
            elif pos == 'attributes':
                for child in spec.getiterator('attribute'):
                    # The element should only have attributes:
                    # - name (mandatory),
                    # - add, remove, separator
                    # - any attribute that starts with data-oe-*
                    unknown = [
                        key
                        for key in child.attrib
                        if key not in ('name', 'add', 'remove', 'separator')
                        and not key.startswith('data-oe-')
                    ]
                    if unknown:
                        raise ValueError(_lt(
                            "Invalid attributes %s in element <attribute>",
                            ", ".join(map(repr, unknown)),
                        ))

                    attribute = child.get('name')
                    value = None

                    if child.get('add') or child.get('remove'):
                        if child.text:
                            raise ValueError(_lt(
                                "Element <attribute> with 'add' or 'remove' cannot contain text %s",
                                repr(child.text),
                            ))
                        value = node.get(attribute, '')
                        add = child.get('add', '')
                        remove = child.get('remove', '')
                        separator = child.get('separator')

                        if attribute in PYTHON_ATTRIBUTES or attribute.startswith('decoration-'):
                            # attribute containing a python expression
                            separator = separator.strip()
                            if separator not in ('and', 'or'):
                                raise ValueError(_lt(
                                    "Invalid separator %(separator)s for python expression %(expression)s; "
                                    "valid values are 'and' and 'or'",
                                    separator=repr(separator), expression=repr(attribute),
                                ))
                            if remove:
                                if re.match(rf'^\(*{remove}\)*$', value):
                                    value = ''
                                else:
                                    patterns = [
                                        f"({remove}) {separator} ",
                                        f" {separator} ({remove})",
                                        f"{remove} {separator} ",
                                        f" {separator} {remove}",
                                    ]
                                    for pattern in patterns:
                                        index = value.find(pattern)
                                        if index != -1:
                                            value = value[:index] + value[index + len(pattern):]
                                            break
                            if add:
                                value = f"({value}) {separator} ({add})" if value else add
                        else:
                            if separator is None:
                                separator = ','
                            elif separator == ' ':
                                separator = None    # squash spaces
                            values = (s.strip() for s in value.split(separator))
                            to_add = filter(None, (s.strip() for s in add.split(separator)))
                            to_remove = {s.strip() for s in remove.split(separator)}
                            value = (separator or ' ').join(itertools.chain(
                                (v for v in values if v and v not in to_remove),
                                to_add
                            ))
                    else:
                        value = child.text or ''

                    if value:
                        node.set(attribute, value)
                    elif attribute in node.attrib:
                        del node.attrib[attribute]
            elif pos == 'inside':
                # add a sentinel element at the end, insert content of spec
                # before the sentinel, then remove the sentinel element
                sentinel = E.sentinel()
                node.append(sentinel)
                add_stripped_items_before(sentinel, spec, extract)
                remove_element(sentinel)
            elif pos == 'after':
                # add a sentinel element right after node, insert content of
                # spec before the sentinel, then remove the sentinel element
                sentinel = E.sentinel()
                node.addnext(sentinel)
                if node.tail is not None:  # for lxml >= 5.1
                    sentinel.tail = node.tail
                    node.tail = None
                add_stripped_items_before(sentinel, spec, extract)
                remove_element(sentinel)
            elif pos == 'before':
                add_stripped_items_before(node, spec, extract)

            else:
                raise ValueError(_lt("Invalid position attribute: '%s'", pos))

        else:
            attrs = ''.join([
                ' %s="%s"' % (attr, html_escape(spec.get(attr)))
                for attr in spec.attrib
                if attr != 'position'
            ])
            tag = "<%s%s>" % (spec.tag, attrs)
            raise ValueError(
                _lt("Element '%s' cannot be located in parent view", tag)
            )

    return source
