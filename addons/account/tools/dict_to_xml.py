from lxml import etree
from odoo.tools.xml_utils import remove_control_characters


def dict_to_xml(node, *, nsmap={}, template=None, render_empty_nodes=False, tag=None, path=None):
    """ Helper to render a Python dict as an XML node.

    The dict is expected to be of the form:
    {
        # Special keys:
        '_tag': 'tag_name',  # '_tag' is rendered as the node's tag
        '_text': 'content',  # '_text' is rendered as the node's text content
        '_dummy': 'dummy_value',  # Keys starting with '_' are not rendered

        # Simple values are rendered as attributes
        'attribute_name': 'attribute_value',

        # Dicts are rendered as child nodes
        'child_tag': {
            '_text': 'content',
            'attribute_name': 'attribute_value',
        },

        # Lists of dicts are also rendered as child nodes
        'child_tag': [
            {
                '_text': 'content',
                'attribute_name': 'attribute_value',
            },
        ],
    }

    :param node: The Python dict to render.
    :param nsmap: (optional) A dict of namespaces to be used for rendering the node.
    :param template: (optional) A Python dict providing default values and an order of keys for rendering the node.
    :param render_empty_nodes: (optional) If True, empty nodes will be rendered in the XML tree.
    :param tag: (optional) The tag of the node to render (needed only for recursive calls).
    :param path: (optional) The path of the currently rendered node in the XML tree (needed only for recursive calls).
    :return: The rendered XML node as an lxml.Element.
    """
    def convert_tag_to_lxml_convention(tag):
        if ':' in tag:
            namespace, local_name = tag.split(':')
            if namespace in nsmap:
                return etree.QName(nsmap[namespace], local_name).text
        return tag

    if template is not None:
        # Ensure order of keys
        node = dict.fromkeys(template) | node

    tag = node.get('_tag') or (template or {}).get('_tag', tag)

    if tag is None:
        raise ValueError(f"No tag was specified for node: {str(node)[:20]}")

    if path is None:
        path = tag

    element = etree.Element(convert_tag_to_lxml_convention(tag), nsmap=nsmap)

    # Add attributes
    for attr_name, attr_value in node.items():
        if not attr_name.startswith('_') and not isinstance(attr_value, (dict, list)) and attr_value is not None and attr_value is not False:
            element.set(convert_tag_to_lxml_convention(attr_name), str(attr_value))

    # Add text content if present
    text = node.get('_text')
    if text is not None and text is not False:
        element.text = remove_control_characters(str(text).encode()).decode()

    # Add child nodes
    for child_tag, child in node.items():
        if not child_tag.startswith('_') and isinstance(child, (dict, list)):
            child_template = (template or {}).get(child_tag)
            child_is_empty = True
            if isinstance(child, dict):
                child = [child]

            # child is a list (of dicts)
            for sub_child in child:
                if sub_child is not None:
                    child_element = dict_to_xml(
                        sub_child,
                        nsmap=nsmap,
                        template=child_template,
                        render_empty_nodes=render_empty_nodes,
                        tag=child_tag,
                        path=f'{path}/{child_tag}',
                    )
                    if child_element is not None:
                        element.append(child_element)
                        child_is_empty = False

            # Check that all non-empty child nodes are defined in the template
            if template is not None and child_tag not in template and not child_is_empty:
                raise ValueError(f"The following child node is not defined in the template: {path}/{child_tag}")

    if not render_empty_nodes and not element.attrib and not element.text and len(element) == 0:
        return None

    return element
