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

        # avoid having only 1 <model> as a root. See also: `_fix_multiple_roots`
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
    :return: List of model instruction dictionaries.
    """

    def parse_model(model_elem):
        # required attributes on <model>
        model_name = model_elem.get('name')
        if not model_name:
            msg = (
                "Missing required 'name' attribute on <model> element. "
                "Each <model> must specify the Odoo model name."
            )
            raise ValueError(msg)

        model_data = {
            'name': model_name,
            'fields': {},
        }
        # optional attributes on <model>
        if count := model_elem.get('count'):
            model_data['count'] = int(count)
        if scale := model_elem.get('scale'):
            model_data['scale'] = str2bool(scale)
        if type_ := model_elem.get('type'):
            model_data['type'] = type_
        if ref := (model_elem.get('id') or model_elem.get('ref')):
            model_data['ref'] = ref
        if domain := model_elem.get('domain'):
            model_data['domain'] = domain
        if parallel := model_elem.get('parallel'):
            model_data['parallel'] = str2bool(parallel)
        if context := model_elem.get('context'):
            model_data['context'] = literal_eval(context)

        return model_data

    def parse_field(field_elem):
        field_data = {}

        for attr_name, attr_value in field_elem.attrib.items():
            # `name` is the key for each field
            if attr_name == 'name':
                continue
            if attr_name in ('count', 'std') and attr_value.isdigit():
                field_data[attr_name] = int(attr_value)
            elif attr_name == 'virtual' and attr_value.lower() in ('true', 'false'):
                field_data[attr_name] = str2bool(attr_value)
            else:
                field_data[attr_name] = attr_value

        nested_fields = field_elem.findall('field')
        if nested_fields:
            field_data['fields'] = {}
            for nested_field in nested_fields:
                nested_name = nested_field.get('name')
                if not nested_name:
                    msg = "Missing required 'name' attribute on a nested <field> element."
                    raise ValueError(msg)

                field_data['fields'][nested_name] = parse_field(nested_field)

        return field_data

    root = etree.fromstring(xml)
    json = []
    for model_elem in root.findall('model'):
        model_data = parse_model(model_elem)

        for field_elem in model_elem.findall('field'):
            field_name = field_elem.get('name')
            if not field_name:
                raise ValueError(
                    f"Missing required 'name' attribute on <field> element "
                    f"in model '{model_data['name']}'. Each <field> must have a 'name'.",
                )

            field_data = parse_field(field_elem)
            model_data['fields'][field_name] = field_data

        json.append(model_data)

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
