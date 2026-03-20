from __future__ import annotations

import logging
import re
from itertools import count
from typing import Callable, NamedTuple
from lxml import etree

new_node_id = count()
next(new_node_id)


class ArchItem(NamedTuple):
    tag_name: str | None
    attribute_spaces: dict  # Dictionary of attributes linked to the spaces that precede them
    end_space: str  # Space between the last attribute and the closing chevron
    auto_close: bool  # Was the tag closed beforehand (to avoid converting </node> to .../>)?
    node_id: int  # Node identifier used during the process


emptyItem = ArchItem(None, {}, '', True, 0)


FLAGS = re.X | re.DOTALL | re.IGNORECASE | re.MULTILINE

NODE_REG = re.compile(r"""
    <(?P<tag_name>[\w:-]+)
    (?P<attributes>(?:(?P<space>\s+)(?P<attribute>[\w:-]+(?:\.f|\.translate)?=\s*(["']).*?\5))*)
    (?P<end_space>\s*)
    (?P<close> (?:\/?>) | (?:>\s*<\/[\w:-]+\s*>)? )
""", flags=FLAGS)
ATTRIBUTES_SPACE_REG = re.compile(r"""
    (?P<space>\s+)
    (?P<attribute>[\w:.-]+(?:\.f|\.translate)?)
    =
    (?P<quote>["'])(?P<value>.*?)(?P=quote)
""", flags=FLAGS)
NODE_ID_REG = re.compile(r' __uprade__="([0-9]+)"')
INDENT_REG = re.compile(r"(?P<space>\n\s+)$", flags=FLAGS)
INDENT_TEXT_REG = re.compile(r"(?P<space>(?:\n\s+)?)(.*)")
ESCAPE_KEY = "\u2007"
ESCAPE_REG = re.compile(r'[<>"]', flags=FLAGS)
UNESCAPE_REG = re.compile(rf'{ESCAPE_KEY}(&lt;|&gt;|&quot;)?', flags=FLAGS)

log = logging.getLogger(__name__)


def update_etree(origin: str, callback: Callable[[etree._ElementTree]]) -> str:
    """
    Maintain indentation in code including between attributes and in attribute
    values.

    To escape/unescape the ", < and > in value and keep the original formatting,
    the feature use an unsecable space (\u2007). Normally these elements should
    have been escaped (or use ')

    You can use the attributes __need_dedent__="4" to dedent 4 spaces in the
    node
    """
    encode, template = origin.split('\n', 1) if origin.startswith('<?xml') else (None, origin)
    start_space = template.split('<', 1)[0]
    end_space = template.rsplit('>', 1)[-1]

    # Etree removes \n and escape > and < in attribute values
    # So you must escape it.

    template = ATTRIBUTES_SPACE_REG.sub(_escape_newlines_in_attr, template)

    # etree does not preserve spaces between attributes
    # So you have to parse the document, associate the etree elements with the
    # spaces and reapply them after the tostring

    structure = iter([
        ArchItem(
            tag_name=match.group('tag_name'),
            attribute_spaces={
                attr: (space, quote, value)
                for space, attr, quote, value in ATTRIBUTES_SPACE_REG.findall(match.group('attributes'))},
            end_space=match.group('end_space'),
            auto_close=match.group('close').startswith('/'),
            node_id=str(next(new_node_id))
        )
        for match in NODE_REG.finditer(template)
    ])

    arch: dict[etree._Element, str, ArchItem] = {}
    root = etree.fromstring(template)
    ref_template = etree.tostring(root, encoding='unicode')
    for el in root.iter(tag=etree.Element):
        xml_tag_name = etree.QName(el.tag).localname if el.nsmap else el.tag
        while ref := next(structure, None):
            if ref[0] == xml_tag_name or ref[0].endswith(f':{xml_tag_name}'):
                arch[el] = ref
                break
        else:
            break

    # apply changes
    callback(root)

    if ref_template == etree.tostring(root, encoding='unicode'):
        return origin

    _dedent_node(root)

    # add node_id on every node to have a reference when we update the string
    for el in root.iter(tag=etree.Element):
        if ref := arch.get(el):
            el.attrib['__uprade__'] = ref.node_id

    # re-insert spaces between attributes
    new_arch: dict[str, ArchItem] = {}
    for el in root.iter(tag=etree.Element):
        item = arch.get(el, emptyItem)
        need_dedent = int(el.attrib.pop('__need_dedent_attributes__', 0))
        node_id = item.node_id
        if not node_id:
            # new nodes
            node_id = str(next(new_node_id))
            el.attrib['__uprade__'] = node_id
        arch_item = ArchItem(
            tag_name=etree.QName(el.tag).localname if el.nsmap else el.tag,
            attribute_spaces=_get_attribute_spaces(arch, el, need_dedent),
            end_space=_get_dedent_space(item.end_space, need_dedent),
            auto_close=item.auto_close,
            node_id=node_id,
        )
        new_arch[node_id] = arch_item

    new_template = etree.tostring(root, encoding='unicode')

    # unescape \n in attribute values
    indented_template = ATTRIBUTES_SPACE_REG.sub(_un_escape_newlines_in_attr, new_template)

    for match in NODE_REG.finditer(indented_template):
        node_xml = match.group(0)
        xml_tag_name = match.group('tag_name')
        xml_attributes = match.group('attributes')
        xml_space = match.group('end_space')
        xml_close = match.group('close')

        node_match = NODE_ID_REG.search(xml_attributes)
        xml_attributes = NODE_ID_REG.sub('', xml_attributes)
        node_id = node_match and node_match.group(1)
        ref = new_arch.get(node_id)

        if ref:
            if ref.attribute_spaces:
                xml_attributes = ATTRIBUTES_SPACE_REG.sub(lambda m: _format_attributes(m, ref.attribute_spaces), xml_attributes)

            if ref.end_space:
                xml_space = ref.end_space

        if ref and not ref.auto_close and xml_close.startswith('/'):
            new_node_xml = f"<{xml_tag_name}{xml_attributes}{xml_space}></{xml_tag_name}>"
        else:
            new_node_xml = f"<{xml_tag_name}{xml_attributes}{xml_space}{xml_close}"

        indented_template = indented_template.replace(node_xml, new_node_xml, 1)

    # test if indent does not fail
    try:
        etree.fromstring(indented_template)
    except Exception as e:  # noqa: BLE001
        log.warning('Wrong template conversion:\n%s\n%s', indented_template, e)
        return origin

    result = f'{start_space}{indented_template}{end_space}'
    return f'{encode}\n{result}' if encode else result


def get_indentation(node: etree._ElementTree) -> str:
    """ return the current xml node indentation
    """
    if (prev := node.getprevious()) is not None:
        match = INDENT_REG.search(prev.tail or '')
    else:
        match = INDENT_REG.search(node.getparent().text or '')
    return '\n' + (match and match.group(0).split('\n').pop() or '')


def _escape_newlines_in_attr(match):
    space = match.group('space')
    attribute = match.group('attribute')
    quote = match.group('quote')
    value = match.group('value')
    escaped_value = ESCAPE_REG.sub(rf'{ESCAPE_KEY}\g<0>', value)
    escaped_value = escaped_value.replace('\n', ESCAPE_KEY)
    return f"{space}{attribute}={quote}{escaped_value}{quote}"


def _un_escape_newlines_in_attr(match):
    space = match.group('space')
    attribute = match.group('attribute')
    quote = match.group('quote')
    value = match.group('value')

    whole = match.group(0)
    if ESCAPE_KEY not in value and '"' not in value:
        return whole

    def unescape(match):
        char = match.group(1)
        if char == '&lt;':
            char = '<'
        elif char == '&gt;':
            char = '>'
        elif char == '&quot;':
            char = '"'
        else:
            char = '\n'
        return char
    unescaped_value = UNESCAPE_REG.sub(unescape, value)

    if '"' in unescaped_value:
        quote = "'"

    return f"{space}{attribute}={quote}{unescaped_value}{quote}"


def _get_dedent_space(space, need_dedent):
    return space[0:-int(need_dedent)] if need_dedent and INDENT_REG.search(space) and len(space) > int(need_dedent) else space


def _get_declared_namespaces(element):
    """Return the newest declared namespaces"""
    current_nsmap = element.nsmap
    if not current_nsmap:
        return {}
    parent = element.getparent()
    if parent is not None:
        parent_nsmap = parent.nsmap
    else:
        parent_nsmap = {}
    newly_declared = {}
    for prefix, uri in current_nsmap.items():
        if prefix not in parent_nsmap or parent_nsmap.get(prefix) != uri:
            newly_declared[f'xmlns:{prefix}'] = uri
    return newly_declared


def _get_attribute_spaces(arch, el, need_dedent):
    attrib = {key: value for key, value in el.attrib.items() if key != '__uprade__'}
    attrib = dict(_get_declared_namespaces(el), **attrib)
    if not len(attrib):
        return {}
    spaces = [arch.get(el, (None, {}, ' '))[1].get(attr, (None, '"', None))[0] for attr in attrib]
    nb_space = max([0] + [len(s) for s in spaces if s is not None])  # auto indent new attribute from other attributes
    has_new_attr = any(v is None for v in spaces)
    has_old_attr = any(v is not None for v in spaces)

    if has_new_attr and (has_old_attr and nb_space > 3 or len(attrib) > 3 or len(''.join(attrib.keys()) + ''.join(attrib.values())) > 80):
        if nb_space < 4:  # auto indent new attribute from closed char '>' indentation
            tag_tail_space = arch.get(el, (None, {}, ' '))[2]
            nb_space = max([len(tag_tail_space), nb_space])
        if nb_space < 4:  # auto indent new attribute from the indentation node
            tag_indent_space = get_indentation(el)
            nb_space = max(nb_space, len(tag_indent_space) + 4)

    indent = ('\n' + ' ' * (nb_space - 1)) if has_new_attr and nb_space > 2 else ' '

    attributes = {}
    for attr in attrib:
        space, quote, value = arch.get(el, (None, {}, ' '))[1].get(attr, (None, '"', None))
        attributes[attr] = (_get_dedent_space(space, need_dedent) if space else indent, quote, value)

    return attributes


def _format_attributes(match, ref_attributes):
    space = match.group('space')
    attribute = match.group('attribute')
    quote = match.group('quote')
    value = match.group('value')
    (ref_space, ref_quote, _ref_value) = ref_attributes.get(attribute, (None, '"', None))
    if ref_quote:
        quote = ref_quote
    if '"' in value:
        quote = "'"
    return f"{ref_space or space}{attribute}={quote}{value}{quote}"


def _dedent_node(root):
    for to_dedent in root.xpath('//*[@__need_dedent__]'):
        need_dedent = int(to_dedent.attrib.pop('__need_dedent__'))
        for el in to_dedent.iter():
            if el.tag is not etree.Comment:
                el.attrib['__need_dedent_attributes__'] = str(need_dedent)

            if el == to_dedent:
                continue

            if len(get_indentation(el)) > need_dedent:
                if (prev := el.getprevious()) is not None:
                    prev.tail = prev.tail[0:-need_dedent]
                elif el.getparent().text:
                    el.getparent().text = el.getparent().text[0:-need_dedent]

            # dedent text in node
            match = INDENT_TEXT_REG.findall(el.text or '')
            if any(text and len(space) > need_dedent for space, text in match):
                el.text = ''.join([
                    f'{space[0:-need_dedent] if len(space) > need_dedent else space}{text}'
                    for space, text in match
                ])
            # dedent text tails
            match = INDENT_TEXT_REG.findall(el.tail or '')
            if any(text and len(space) > need_dedent for space, text in match) or el.getnext() is None:
                el.tail = ''.join([
                    f'{space[0:-need_dedent] if len(space) > need_dedent else space}{text}'
                    for space, text in match
                ])


# QUICK TESTING

def _test():
    # ruff: noqa: W293, W291, E222

    template_test = """<?xml version="1.0" encoding="utf-8"?>
    <odoo>
        <template id="test_validated" name="Website test: test Confirmed">
            <t t-if="request.env.user._is_public()" t-set="no_breadcrumbs" t-value="True"/>
            <t t-call="portal.portal_layout">
                <t t-set="test_type" t-value="event.test_type_id"/>
                <t t-set="staff_user" t-value="event.user_id"/>
                <t t-set="resources" t-value="event.test_resource_ids"/>
                <t t-set="based_on_users" t-value="test_type.schedule_based_on == 'users'"/>
                <div id="wrap" class="o_test d-flex bg-o-color-4 p-4">
                <div 
                    class="oe_structure"/>
                    <div
                            class="o_test_edit_in_backend alert alert-info alert-dismissible fade show d-print-none css_editable_mode_hidden"
                            groups="test.group_test_manager">
                        <t t-call="test.test_edit_in_backend"/>
                    </div>
                    <t t-if="test_type and
                        toto + 1">
                        test
                    </t>
                    <t t-if="len(resources)">
                    
                            <article t-foreach="stuff.test" t-as="tata" class="d-flex flex-nowrap gap-2 align-items-center mb-1">
                                <div t-if="tata"
                                    class="o_class_test other_test">
                                    <div t-attf-style="background-image: url('/test/#{test_type.id}/resource_avatar?resource_id=#{resource.id}');"
                                        class="o_test_avatar_background rounded-circle"/>;
                                </div>
                                <t t-out="resource.name"
                                    />
                            </article>
                    </t>
                    <placeholder/>
                </div>
            </t>
        </template>
    </odoo>
    """

    # no change
    assert template_test == update_etree(template_test, lambda el: None)

    # trigger a change
    other_test = update_etree(template_test, lambda el: el.set('__test__', '33'))
    assert '__test__' in other_test
    assert template_test == other_test.replace(' __test__="33"', '')

    # replace a node and move an other with dedent
    def change(el):
        # replace a node
        placeholder = el.xpath('//placeholder')[0]

        parent = placeholder.getparent()
        newnode = etree.Element('newnode', {
            'data-attribute-a': "1",
            'data-attribute-b': "1",
            'data-attribute-c': "1",
            'data-attribute-d': "1",
            'data-attribute-e': "1",
        })
        parent.insert(parent.index(placeholder), newnode)
        newnode.text = "TEST"
        newnode.tail = get_indentation(newnode)

        newnode2 = etree.Element('newnode2', {
            'data-a': "long long long long long long long long long long",
            'data-b': "again again again again again again again again",
        })
        parent.insert(parent.index(placeholder), newnode2)
        newnode2.text = "TEST"
        newnode2.tail = placeholder.tail

        parent.remove(placeholder)

        # move a node to his parent and dedent
        article = el.xpath('//article')[0]
        parent = article.getparent()
        begin_indent = get_indentation(article)
        end_indent = get_indentation(parent)
        article.set('__need_dedent__', str(len(begin_indent) - len(end_indent)))
        parent.text += article.tail
        parent_parent = parent.getparent()
        parent_parent.insert(parent_parent.index(parent), article)

    other_test = update_etree(template_test, change)

    assert other_test == """<?xml version="1.0" encoding="utf-8"?>
    <odoo>
        <template id="test_validated" name="Website test: test Confirmed">
            <t t-if="request.env.user._is_public()" t-set="no_breadcrumbs" t-value="True"/>
            <t t-call="portal.portal_layout">
                <t t-set="test_type" t-value="event.test_type_id"/>
                <t t-set="staff_user" t-value="event.user_id"/>
                <t t-set="resources" t-value="event.test_resource_ids"/>
                <t t-set="based_on_users" t-value="test_type.schedule_based_on == 'users'"/>
                <div id="wrap" class="o_test d-flex bg-o-color-4 p-4">
                <div 
                    class="oe_structure"/>
                    <div
                            class="o_test_edit_in_backend alert alert-info alert-dismissible fade show d-print-none css_editable_mode_hidden"
                            groups="test.group_test_manager">
                        <t t-call="test.test_edit_in_backend"/>
                    </div>
                    <t t-if="test_type and
                        toto + 1">
                        test
                    </t>
                    <article t-foreach="stuff.test" t-as="tata" class="d-flex flex-nowrap gap-2 align-items-center mb-1">
                        <div t-if="tata"
                            class="o_class_test other_test">
                            <div t-attf-style="background-image: url('/test/#{test_type.id}/resource_avatar?resource_id=#{resource.id}');"
                                class="o_test_avatar_background rounded-circle"/>;
                        </div>
                        <t t-out="resource.name"
                            />
                    </article>
                    <t t-if="len(resources)">
                    
                            
                    </t>
                    <newnode
                        data-attribute-a="1"
                        data-attribute-b="1"
                        data-attribute-c="1"
                        data-attribute-d="1"
                        data-attribute-e="1">TEST</newnode>
                    <newnode2
                        data-a="long long long long long long long long long long"
                        data-b="again again again again again again again again">TEST</newnode2>
                </div>
            </t>
        </template>
    </odoo>
    """


if __name__ == '__main__':
    _test()
