import re

from lxml import etree

__all__ = [
    "dict_to_xml",
]

_NOT_XML_CHARACTER_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]"
)


def _xml_characters(value: object) -> str:
    return _NOT_XML_CHARACTER_RE.sub("", str(value))


def dict_to_xml(
    node: dict,
    *,
    nsmap: dict | None = None,
    template: dict | None = None,
    render_empty_nodes: bool = False,
    tag: str | None = None,
    path: str | None = None,
) -> etree._Element | None:
    if nsmap is None:
        nsmap = {}

    def convert_tag_to_lxml_convention(tag: str) -> str:
        if ":" in tag:
            namespace, local_name = tag.split(":", 1)
            if namespace in nsmap:
                return etree.QName(nsmap[namespace], local_name).text
        return tag

    if template is not None:
        node = dict.fromkeys(template) | node

    tag = node.get("_tag") or (template or {}).get("_tag", tag)

    if tag is None:
        raise ValueError(f"No tag was specified for node: {str(node)[:20]}")

    if path is None:
        path = tag

    element = etree.Element(convert_tag_to_lxml_convention(tag), nsmap=nsmap)

    for attr_name, attr_value in node.items():
        if (
            not attr_name.startswith("_")
            and not isinstance(attr_value, (dict, list))
            and attr_value is not None
            and attr_value is not False
        ):
            element.set(
                convert_tag_to_lxml_convention(attr_name), _xml_characters(attr_value)
            )

    text = node.get("_text")
    if text is not None and text is not False:
        element.text = _xml_characters(text)

    for child_tag, child in node.items():
        if not child_tag.startswith("_") and isinstance(child, (dict, list)):
            child_template = (template or {}).get(child_tag)
            child_is_empty = True
            if isinstance(child, dict):
                child = [child]

            for sub_child in child:
                if sub_child is not None:
                    child_element = dict_to_xml(
                        sub_child,
                        nsmap=nsmap,
                        template=child_template,
                        render_empty_nodes=render_empty_nodes,
                        tag=child_tag,
                        path=f"{path}/{child_tag}",
                    )
                    if child_element is not None:
                        element.append(child_element)
                        child_is_empty = False

            if (
                template is not None
                and child_tag not in template
                and not child_is_empty
            ):
                raise ValueError(
                    f"The following child node is not defined in the template: {path}/{child_tag}"
                )

    if (
        not render_empty_nodes
        and not element.attrib
        and not element.text
        and len(element) == 0
    ):
        return None

    return element
