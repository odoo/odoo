from __future__ import annotations

from ast import literal_eval
from typing import TYPE_CHECKING

from lxml import etree

from odoo.tools import str2bool, template_inheritance

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from lxml.etree import _Element as Element


def ensure_root(xml: str) -> str:
    """Wrap XML snippets in the ``<data>`` root expected by blueprint parsing.

    :param xml: Raw XML definition, possibly empty or with multiple root nodes.
    :return: XML string with a single ``<data>`` root element.
    """
    try:
        root = etree.fromstring(xml)

        # avoid having only 1 operation node as a root. See also: `_fix_multiple_roots`
        if root.tag != 'data':
            data_el = etree.Element('data')
            data_el.append(root)
            return etree.tostring(data_el, encoding='unicode')

    except etree.XMLSyntaxError as e:
        if 'Document is empty' in str(e):
            return etree.tostring(etree.Element('data'), encoding='unicode')
        # Usually this error means there are multiple roots -> wrap
        if 'Extra content at the end of the document' in str(e):
            return ensure_root(f'<data>{xml}</data>')
        raise
    else:
        return xml


def parse(xml: str):
    """
    Convert the XML definition into the JSON version.

    Note that this returns Python values representing the JSON; it is not a
    string containing a JSON payload.

    :param xml: Blueprint XML string with a ``<data>`` root.
    :return: List of operation block dictionaries.
    """

    def parse_block(block_elem):
        operation = etree.QName(block_elem).localname

        if block_elem.get('operation'):
            raise ValueError(
                f"<{operation}> cannot define an 'operation' attribute. "
                f"The XML element name already defines the operation.",
            )

        model_name = block_elem.get('model')
        if not model_name:
            msg = (
                f"Missing required 'model' attribute on <{operation}> element. "
                f"Each <{operation}> must specify the Odoo model name."
            )
            raise ValueError(msg)

        if operation == 'create' and block_elem.get('ref'):
            raise ValueError("<create> cannot define a 'ref' attribute. Use 'id' for create references.")
        if operation in ('write', 'function') and block_elem.get('id'):
            raise ValueError(f"<{operation}> cannot define an 'id' attribute. Use 'ref' for targets.")

        block_data = {
            'operation': operation,
            'model': model_name,
            'fields': {},
            'values': {},
        }
        if operation == 'function':
            block_data['args'] = {}
            if name := block_elem.get('name'):
                block_data['name'] = name
        if count := block_elem.get('count'):
            block_data['count'] = int(count)
        if scale := block_elem.get('scale'):
            block_data['scale'] = str2bool(scale)
        if batched := block_elem.get('batched'):
            block_data['batched'] = str2bool(batched)
        if operation == 'create':
            if ref := block_elem.get('id'):
                block_data['id'] = ref
        elif ref := block_elem.get('ref'):
            block_data['ref'] = ref
        if domain := block_elem.get('domain'):
            block_data['domain'] = domain
        if parallel := block_elem.get('parallel'):
            block_data['parallel'] = str2bool(parallel)
        if context := block_elem.get('context'):
            block_data['context'] = literal_eval(context)

        return block_data

    def parse_target(target_elem):
        target_data = {}

        for attr_name, attr_value in target_elem.attrib.items():
            # `name` is the key for each target
            if attr_name == 'name':
                continue
            if attr_name in ('count', 'std') and attr_value.isdigit():
                target_data[attr_name] = int(attr_value)
            else:
                target_data[attr_name] = attr_value

        return target_data

    root = etree.fromstring(xml)
    json = []
    for block_elem in root:
        if not isinstance(block_elem.tag, str):
            continue

        operation = etree.QName(block_elem).localname
        if operation not in ('create', 'write', 'function'):
            raise ValueError(f"Unsupported populate operation <{operation}>. Expected <create>, <write> or <function>.")

        block_data = parse_block(block_elem)
        arg_index = 0

        for child_elem in block_elem:
            if not isinstance(child_elem.tag, str):
                continue

            child_type = etree.QName(child_elem).localname
            if child_type not in ('field', 'value', 'arg'):
                continue

            target_name = child_elem.get('name')
            if not target_name:
                if child_type == 'arg':
                    target_name = str(arg_index)
                    arg_index += 1
                else:
                    raise ValueError(
                        f"Missing required 'name' attribute on <{child_type}> element "
                        f"in block for model '{block_data['model']}'. Each <{child_type}> must have a 'name'.",
                    )
            elif child_type == 'arg' and target_name.isdecimal():
                arg_index = max(arg_index, int(target_name) + 1)

            target = {
                'field': 'fields',
                'value': 'values',
                'arg': 'args',
            }[child_type]
            block_data.setdefault(target, {})
            if target_name in block_data[target]:
                raise ValueError(
                    f"Duplicate <{child_type}> name '{target_name}' "
                    f"in block for model '{block_data['model']}'.",
                )

            block_data[target][target_name] = parse_target(child_elem)

        json.append(block_data)

    return json


def apply_inheritance(parent_xml: str, xml: str) -> str:
    """Apply child XPath specs to a parent XML blueprint definition.

    :param parent_xml: Resolved parent XML definition.
    :param xml: Child XML definition containing inheritance specs.
    :return: Resolved XML definition.
    """
    parent_tree = etree.fromstring(parent_xml)
    specs_tree = etree.fromstring(xml)
    resolved = apply_inheritance_specs(parent_tree, specs_tree)
    return etree.tostring(resolved, encoding='unicode')


def apply_inheritance_specs(
    source_tree: Element,
    specs: Iterable[Element],
) -> Element:
    """Apply an XML element's inheritance specifications to ``source_tree``."""
    return template_inheritance.apply_inheritance_specs(source_tree, list(specs))


def expand_imports(
    definition: Element,
    resolve_import: Callable[[Element], Element],
) -> Element:
    """Expand top-level imports in an XML element.

    ``resolve_import`` receives each ``<import>`` element and returns a
    ``<data>`` fragment. Its top-level nodes are moved into ``definition``, so
    callers must return a fragment owned by this operation.
    """
    if definition.xpath('.//import[not(parent::data) and not(ancestor::import)]'):
        raise ValueError("<import> must be a direct child of <data>.")

    for element in list(definition.iterchildren('import')):
        fragment = resolve_import(element)
        for block in list(fragment):
            element.addprevious(block)
        definition.remove(element)

    return definition


def namespace_references(fragment_tree: Element, namespace: str) -> None:
    """Prefix a fragment's declared IDs and internal refs with ``namespace``."""
    declared_ids: set[str] = {
        ref
        for block in fragment_tree.iterchildren('create')
        if (ref := block.get('id'))
    }
    for block in fragment_tree:
        if block.get('id') in declared_ids:
            block.set('id', f"{namespace}/{block.get('id')}")

        for element in block.iter():
            if not (ref := element.get('ref')):
                continue
            base_ref, separator, relation_path = ref.partition('.')
            if base_ref in declared_ids:
                element.set('ref', f'{namespace}/{base_ref}{separator}{relation_path}')
