from __future__ import annotations

import logging
import re
import typing

from lxml import etree

from odoo.upgrade_code.tools_etree import get_indentation, update_etree

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager

AUTO_CLOSE_T = re.compile(r"(<t [^>]*[^/>])>\s*</t>", flags=re.MULTILINE)
XPATH_TCALL_REG = re.compile(r'\[@(t-call|t-snippet-call)=[^\]]+\]$')

log = logging.getLogger(__name__)


def upgrade(file_manager: FileManager):
    files = [file for file in file_manager if file.path.suffix == '.xml' and '/static/' not in str(file.path)]
    if not files:
        return

    def detach_node_tail(node):
        if (prev := node.getprevious()) is not None:
            prev.tail = (prev.tail or '').rstrip() + (node.tail or '')
        else:
            parent = node.getparent()
            parent.text = (parent.text or '').rstrip() + (node.tail or '')

    def move_tset_before_tcall(tset, tcall):
        parent = tcall.getparent()
        previous_indent = get_indentation(tset)
        indent = get_indentation(tcall)

        detach_node_tail(tset)
        tset.tail = indent

        tset.set('__need_dedent__', str(len(previous_indent) - len(indent)))

        parent.insert(parent.index(tcall), tset)

    def remove_tset_add_attribute(tset, tcall):
        detach_node_tail(tset)

        if 't-value' in tset.attrib:
            value = tset.get('t-value')
            if value.startswith("'") and value.endswith("'") and "{" not in value and "'" not in value[1:-1]:
                tcall.set(f"{tset.get('t-set')}.f", value[1:-1])
            else:
                tcall.set(tset.get('t-set'), value)
        elif 't-valuef' in tset.attrib:
            tcall.set(f"{tset.get('t-set')}.f", tset.get('t-valuef'))
        else:
            tcall.set(f"{tset.get('t-set')}.translate", (tset.text or '').strip())

        tset.getparent().remove(tset)

    def is_not_direct_children_of(tset, tcall):
        closest_tcall = tset.xpath('ancestor::t[@t-call or @t-snippet-call or @t-if or @t-elif or @t-else or @t-set or @t-foreach]')
        return closest_tcall and closest_tcall[-1] != tcall

    def varname_is_used_inside(tset, tcall):
        n = tset
        while (skip_to := n.getnext()) is None and n != tcall:
            n = n.getparent()
        if skip_to is None:
            return set()
        return _varname_is_used_inside(tset, tcall, skip_to)

    def _varname_is_used_inside(tset, container, skip_to):
        used = set()
        varname = tset.get('t-set')
        REG = re.compile(rf"(^|[,({{ /*+-]){ varname }([\[\] .()}})/*+-]|$)")

        for el in container.iter():
            if skip_to is not None and el is not skip_to:
                continue
            skip_to = None
            if not el.tag:
                continue

            # For the t-set using this value, we check if this new value is used
            # in the template and continue to check the other usecases.
            # If the varname is used, if is used by an other unused t-set, we
            # need to move the current t-set before the t-call.
            # If the varname is use only by attribute and t-set also used, the
            # current t-set does'nt move.
            for attr, value in el.attrib.items():
                if not attr.startswith('t-'):
                    if el.attrib.get('t-call') and REG.search(value):
                        used.add('used')
                elif attr == 't-set' or attr == 't-as':
                    if value == varname:
                        closest_tcall = el.xpath('ancestor::t[@t-call or @t-snippet-call]')
                        if closest_tcall and closest_tcall[-1] == container:
                            used.add('rewrite')
                elif REG.search(value):
                    used.add('current-used')

            is_tset = el.get('t-set')
            if is_tset:
                # get if the value is used inside an other t-set
                if len(el) and _varname_is_used_inside(tset, el, el[0]):
                    used.add('current-used')
                skip_to = el.getnext()

            if 'current-used' in used:
                used.remove('current-used')
                if is_tset:
                    sub_used = varname_is_used_inside(el, container) - {'rewrite'}
                    if sub_used:
                        used.update(sub_used)
                    else:
                        if is_not_direct_children_of(tset, container):
                            used.add('used')
                        else:
                            used.add('t-set')
                else:
                    used.add('used')

        return used

    def remove_tset_add_inherit_attribute(tset, container):
        attribute = etree.Element('attribute')
        if len(container):
            container[-1].tail = container.text  # indent
        container.append(attribute)

        if 't-value' in tset.attrib:
            value = tset.get('t-value')
            if value.startswith("'") and value.endswith("'") and "{" not in value and "'" not in value[1:-1]:
                attribute.attrib['name'] = f"{tset.get('t-set')}.f"
                attribute.text = value[1:-1]
            else:
                attribute.attrib['name'] = tset.get('t-set')
                attribute.text = value
        elif 't-valuef' in tset.attrib:
            attribute.attrib['name'] = f"{tset.get('t-set')}.f"
            attribute.text = tset.get('t-valuef')
        elif not len(tset):
            attribute.attrib['name'] = f"{tset.get('t-set')}.translate"
            attribute.text = (tset.text or '').strip()
        else:
            raise ValueError('Wrong conversion')

        if tset.getparent() is not None:
            tset.getparent().remove(tset)

    def change(root: etree._ElementTree):
        for tcall in root.xpath('//*[@t-call or @t-snippet-call][not(@position="inside")]'):

            if any(not att.startswith('t-') for att in tcall.attrib):
                continue
            if tcall.xpath('ancestor::kanban'):
                continue

            # every t-set children
            for tset in tcall.xpath('.//*[@t-set]'):
                if is_not_direct_children_of(tset, tcall):
                    # not in a directive (as t-if, t-foreach...) or an other
                    # t-set and not in an other t-call
                    continue

                used = varname_is_used_inside(tset, tcall)

                if 'used' in used:
                    # This set of characters is used within the current content.
                    # It is presumably not used by the t-call.
                    continue

                if 'rewrite' in used:
                    raise ValueError(f"Can not determine the position of the rewrited t-set: {tset.get('t-set')!r}")

                # Move the t-set if the are some content or if it's used for an
                # other t-set else we can remove it and add as an attribute.
                if ('t-set' in used or
                   (
                        len(tset) or
                        tset.get('groups') or
                        tset.get('t-groups') or
                        tset.get('t-if')
                   )):
                    # Move the t-set if the are some content or if it's used
                    # for an other t-set
                    move_tset_before_tcall(tset, tcall)
                    tcall.set(tset.get('t-set'), tset.get('t-set'))
                else:
                    # never used inside we can remove it and add as an attribute.
                    remove_tset_add_attribute(tset, tcall)

        # # if we need to have an idem potent change
        # for tcall in root.xpath('//*[@t-call or t-snippet-call][not(@position="inside")]'):
        #     if not any(not att.startswith('t-') for att in tcall.attrib) and tcall.xpath('*[@t-set]'):
        #         tcall.set('true', 'True')

        # inherit t-call
        inherit_tcalls = (
            root.xpath('//*[@t-call or t-snippet-call][@position="inside"]') +
            [
                tcall for tcall in root.xpath('//xpath[contains(@expr, "@t-call") or contains(@expr, "@t-snippet-call")][@position="inside"]')
                if XPATH_TCALL_REG.search(tcall.get('expr'))
            ]
        )
        for tcall in inherit_tcalls:
            parent = tcall.getparent()
            index = parent.index(tcall)
            indent = get_indentation(tcall)
            before = None
            attributes = None
            for tset in tcall.xpath('t[@t-set]'):
                detach_node_tail(tset)

                if attributes is None:
                    attributes = etree.Element(tcall.tag, tcall.attrib)
                    attributes.attrib['position'] = 'attributes'
                    attributes.text = indent + ' ' * 4
                    attributes.tail = indent
                    parent.insert(index, attributes)

                t_set_key = tset.get('t-set')
                if len(tset) or varname_is_used_inside(tset, tcall):
                    if before is None:
                        before = etree.Element(tcall.tag, tcall.attrib)
                        before.attrib['position'] = 'before'
                        before.text = indent + ' ' * 4
                        before.tail = indent
                        parent.insert(index, before)

                    before.append(tset)
                    tset = etree.Element('t', {'t-set': t_set_key, 't-value': t_set_key})

                remove_tset_add_inherit_attribute(tset, attributes)

            if before is not None:
                before[-1].tail = indent
            if attributes is not None:
                attributes[-1].tail = indent

            if not len(tcall):
                detach_node_tail(tcall)
                parent.remove(tcall)

    for fileno, file in enumerate(files, start=1):

        try:
            content = file.content

            if ('t-call=' in content or 't-snippet-call=' in content) and 't-set=' in content:
                content = update_etree(content, change)
                content = AUTO_CLOSE_T.sub(r"\g<1>/>", content)
                file.content = content
        except Exception as e:  # noqa: BLE001
            log.warning("Can not update: %s because: %s", file.path, e)
            continue

        file_manager.print_progress(fileno, len(files))
