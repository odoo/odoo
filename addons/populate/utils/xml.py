from ast import literal_eval

from lxml import etree

from odoo.tools import str2bool, template_inheritance


def ensure_root(xml):
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


def parse(xml):
    """
    Convert the XML definition into the JSON version.

    Note that this returns Python values representing the JSON; it is not a
    string containing a JSON payload.

    :param xml: Blueprint XML string with a ``<data>`` root.
    :return: List of operation block dictionaries.
    """

    def parse_block(block_elem):
        block_type = etree.QName(block_elem).localname

        if block_elem.get('type'):
            raise ValueError(
                f"<{block_type}> cannot define a 'type' attribute. "
                f"The XML tag already defines the operation type.",
            )

        model_name = block_elem.get('model')
        if not model_name:
            msg = (
                f"Missing required 'model' attribute on <{block_type}> element. "
                f"Each <{block_type}> must specify the Odoo model name."
            )
            raise ValueError(msg)

        if block_type == 'create' and block_elem.get('ref'):
            raise ValueError("<create> cannot define a 'ref' attribute. Use 'id' for create references.")
        if block_type in ('write', 'function') and block_elem.get('id'):
            raise ValueError(f"<{block_type}> cannot define an 'id' attribute. Use 'ref' for targets.")

        block_data = {
            'type': block_type,
            'model': model_name,
            'fields': {},
            'values': {},
        }
        if block_type == 'function':
            block_data['args'] = {}
            if name := block_elem.get('name'):
                block_data['name'] = name
        if count := block_elem.get('count'):
            block_data['count'] = int(count)
        if scale := block_elem.get('scale'):
            block_data['scale'] = str2bool(scale)
        if batched := block_elem.get('batched'):
            block_data['batched'] = str2bool(batched)
        if block_type == 'create':
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

        block_type = etree.QName(block_elem).localname
        if block_type not in ('create', 'write', 'function'):
            raise ValueError(f"Unsupported populate operation <{block_type}>. Expected <create>, <write> or <function>.")

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


def apply_inheritance(parent_xml, xml):
    """Apply child XPath specs to a parent XML blueprint definition.

    :param parent_xml: Resolved parent XML definition.
    :param xml: Child XML definition containing inheritance specs.
    :return: Resolved XML definition.
    """
    parent_tree = etree.fromstring(parent_xml)
    specs_tree = etree.fromstring(xml)
    resolved = template_inheritance.apply_inheritance_specs(parent_tree, specs_tree)
    return etree.tostring(resolved, encoding='unicode')
