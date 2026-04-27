import re
from bisect import bisect_left
from copy import deepcopy
from itertools import chain
from typing import Literal, Optional
from lxml import etree


## SOME XML UTILS
INDENT_RE = re.compile(r"(^\n[\s\t]*)|(\n[\s\t]*$)")


def append_text(node, text):
    if len(node) > 0:
        node[-1].tail = text
    else:
        node.text = text


def dedent_tree(elem):
    for el in elem.iter(etree.Element):
        if el.text is not None:
            el.text = INDENT_RE.sub("", el.text) or None
        if el.tail is not None:
            el.tail = INDENT_RE.sub("", el.tail) or None


def indent_tree(elem, level=1, spaces=2):
    """
    The lxml library doesn't pretty_print xml tails, this method aims
    to solve this.

    Returns the elem with properly indented text and tail
    """
    # See: http://lxml.de/FAQ.html#why-doesn-t-the-pretty-print-option-reformat-my-xml-output
    # Below code is inspired by http://effbot.org/zone/element-lib.htm#prettyprint
    indent_texts = elem.tag == "xpath"

    len_elem = len(elem)
    if len_elem:
        i = "\n" + level * spaces * " "
        prev_i = "\n" + (level - 1) * spaces * " "

        if indent_texts or (not elem.text or not elem.text.strip()):
            text = elem.text
            elem.text = (text.strip() + i) if text else i
        index = 0
        while (index < len_elem):
            subelem = elem[index]
            tail = (subelem.tail or "").strip()
            if indent_texts or not tail:
                if index == len_elem - 1:
                    subelem.tail = (i + tail + prev_i) if tail else prev_i
                else:
                    subelem.tail = (i + tail + i) if tail else i
            indent_tree(subelem, level + 1, spaces)
            index += 1
    return elem


def visit(node, do_children: lambda n: True):
    yield node
    if do_children(node) is False:
        return
    for child in node.iterchildren(etree.Element):
        yield from visit(child, do_children)


## TOOLS TO MAKE THE DIFF
def diff_dicts(old: etree._Attrib, new: etree._Attrib, ignored_keys: Optional[set] = frozenset()) -> dict:
    return {
        k: new.get(k) for k in sorted(set().union(old, new))
        if k not in ignored_keys and old.get(k) != new.get(k)
    }


def longest_increasing_subsequence(arr):
    """Returns the longest increasing subsequence of a list of unordered values
    Largely inspired from https://en.wikipedia.org/wiki/Longest_increasing_subsequence
    and by https://cp-algorithms.com/sequences/longest_increasing_subsequence.html

    It compares items on their value: in the case items are string: "11" < "2" == True.
    So, transforming an item to its value if necessary should be done before hand

    As it returns the biggest list of stable elements in the list,
    it is useful to compute the least amount of moving items into that list

    eg: [3,1,2] : 1 and 2 did not move, 3 is just placed before 1
    longest_increasing_subsequence = [1,2]
    """
    if not arr:
        return []

    previous = {}
    first, *list_arr = arr
    smallest_endings = [first]
    for el in list_arr:
        if el < smallest_endings[-1]:
            target_index = bisect_left(smallest_endings, el)
            previous[el] = smallest_endings[target_index - 1]
            smallest_endings[target_index] = el
        else:
            previous[el] = smallest_endings[-1]
            smallest_endings.append(el)

    sequence = []
    el = smallest_endings[-1]
    for _el in smallest_endings:
        sequence.append(el)
        el = previous.get(el)

    return sequence


def _get_node_boundary_text(node: etree._Element, position: Literal["before", "after", "inside"]) -> str | None:
    """Given a node and a position, returns the text that will be impacted according
    to Odoo's xpath semantics

    see template_inheritance.py:add_stripped_items_before
    """
    if position == "before":
        prev = node.getprevious()
        if prev is not None:
            return prev.tail
        else:
            return node.getparent().text
    if position == "after":
        return node.tail
    if position == "inside":
        if len(node) > 0:
            return node[-1].tail
        else:
            return node.text


def _group_leafs(leafs: list, l_i_s: set):
    """Group the leafs according to their reference node and position. Similar to
    itertools.groupy, except it needed to be "read ahead" as the target of a leaf
    can be before any stable node (the ones in the l_i_s set)

    :param: set l_i_s: the longest increasing subsequence indicating stable node's ids
    """
    last_stable = None
    no_targets = []
    current_group = []
    current_key = None

    for leaf in leafs:
        if leaf.get("id") in l_i_s:
            last_stable = leaf["id"]
            if no_targets:
                yield (last_stable, "before"), no_targets
                no_targets = []
        elif last_stable:
            new_key = (last_stable, "after")
            if new_key == current_key:
                current_group.append(leaf)
            else:
                if current_key and current_group:
                    yield current_key, current_group
                current_group = [leaf]
                current_key = new_key
        else:
            no_targets.append(leaf)

    if current_group:
        yield current_key, current_group

    if no_targets:
        yield (last_stable, "inside"), no_targets


DIFF_ATTRIBUTE = "o-diff-key"


class KeyedXmlDiffer:
    """A class that allows to compute the difference between two trees, of which we know one is a modification of the other.
    Namely, both trees have nodes that have a unique ID, each node in the new tree is compared to its
    counterpart in the old one.
    Hence the recommended flow:
    - assign ids on the original tree
    - ids must be convertible to int, and increasing with the tree's order (depth first)
    - do some operation on that modified tree
    - compare the original tree with the modified one

    It supports moving, removing nodes, altering texts, altering the order of a node's children, modifying attributes of a node
    It doesn't support changing the tag name of a node
    It doesn't support anything else than Elements, in particular, comments and their tail will be ignored

    The `diff` method returns an abstraction describing what happened for a node with a given id
    The `diff_xpath` method computes the Odoo's xpath notation to be used as an inherited view

    The expected complexity is O(n log n), because of the use of bisect.
    It could be higher when we compute the xpath for each touched nodes.
    We still have to browse several times the trees.
    """
    @classmethod
    def assign_node_ids_for_diff(self, tree):
        for index, desc in enumerate(tree.iter(etree.Element)):
            desc.set(DIFF_ATTRIBUTE, str(index))

    def __init__(self,
        ignore_attributes=None,
        on_new_node=lambda n: True,
        is_subtree=lambda n: False,
        xpath_with_meta=False,
    ):
        # User-defined parameters
        self.ignore_attributes = set([] if ignore_attributes is None else ignore_attributes)
        self.__on_new_node = on_new_node
        self.attributes_identifiers = {
            "id": True,
            "name": True,
            "t-name": True,
            "t-call": True,
            "t-field": True,
            "t-set": True,
        }
        self.is_subtree = is_subtree
        self.xpath_with_meta = xpath_with_meta

        # Internal State
        self.changes = {}
        self.map_id_to_node_old = {}

    def _build_tree_from_input(self, diff_input):
        if isinstance(diff_input, (etree._ElementTree, etree._Element)):
            return deepcopy(diff_input)
        else:
            parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
            return etree.fromstring(diff_input, parser=parser)

    # Basic diffing abstraction
    def diff(self, old, new):
        old_tree = self._build_tree_from_input(old)
        new_tree = self._build_tree_from_input(new)

        self.map_id_to_node_old = {node.get(DIFF_ATTRIBUTE): node for node in old_tree.iter(etree.Element)}
        self._diff_nodes(self.map_id_to_node_old[new_tree.get(DIFF_ATTRIBUTE)], new_tree)

        return self.changes

    def _diff_nodes(self, old, new):
        main_node_id = old.get(DIFF_ATTRIBUTE)
        local_map_id_to_node = {}
        old_repr = [(None, old.text)]  # is used to check if there have been any changes (without attributes)
        for index, child in enumerate(old.iterchildren(etree.Element)):
            nid = child.get(DIFF_ATTRIBUTE)
            old_repr.append((nid, child.tail))
            local_map_id_to_node[nid] = (index, child)

        leafs = []  # represents children and texts. They will be grouped according to their nearest unmoving sibling
        new_repr = [(None, new.text)]  # is used to check if there have been any changes (without attributes)
        kept_nodes = []  # nodes' id that are still present
        children_to_diff = {}  # a map id to new node to continue the iteration of the tree
        acquired_nodes = set()  # nodes' ids that are coming from elsewhere in the tree
        removed_nodes = set(local_map_id_to_node)  # children of the main node that will be removed

        leafs.append({"type": "text", "element": INDENT_RE.sub("", new.text) if new.text else new.text})
        for child in new.iterchildren(etree.Element):
            nid = child.get(DIFF_ATTRIBUTE)
            is_owned = nid in local_map_id_to_node
            new_repr.append((nid or False, child.tail))

            if nid:
                children_to_diff[nid] = child
                if is_owned:
                    kept_nodes.append(int(nid))
                    removed_nodes.remove(nid)
                else:
                    acquired_nodes.add(nid)
            else:
                for new_child in self._visit_new_node(child):
                    _nid = new_child.get(DIFF_ATTRIBUTE)
                    if _nid:
                        acquired_nodes.add(_nid)
                        children_to_diff[_nid] = new_child

            leafs.extend([
                {"type": "node", "owned": is_owned, "element": child, "id": nid},
                {"type": "text", "element": INDENT_RE.sub("", child.tail) if child.tail else child.tail}
            ])

        attributes_changes = diff_dicts(old.attrib, new.attrib, self.ignore_attributes)
        has_body_changes = old_repr != new_repr
        if not has_body_changes and not attributes_changes:
            for nid, new_child in children_to_diff.items():
                self._diff_nodes(self.map_id_to_node_old[nid], new_child)
            return

        command = {"attributes": attributes_changes, "new_node": new, "leafs": leafs}
        if has_body_changes:
            l_i_s = {str(k) for k in longest_increasing_subsequence(kept_nodes)}
            children_changes = []
            replace_text = False
            for (target_id, position), grouped in _group_leafs(leafs, l_i_s):
                target_id = target_id or main_node_id
                target_node = self.map_id_to_node_old[target_id]
                old_text = _get_node_boundary_text(target_node, position)
                old_text = old_text and INDENT_RE.sub("", old_text)

                if position == "after":
                    text_leaf = grouped[-1]
                elif position in ("before", "inside"):
                    text_leaf = grouped[0]

                are_texts_compatible = False
                if text_leaf["element"] == old_text:
                    are_texts_compatible = True
                    text_leaf["ignore"] = True

                children_changes.append({
                    "target_id": target_id,
                    "position": position,
                    "replace_text": not are_texts_compatible,
                    "leafs": grouped,
                })
                if not are_texts_compatible:
                    replace_text = True
            command.update(
                removed_nodes=removed_nodes,
                replace_text=replace_text,
                children_changes=children_changes,
                acquired_nodes=acquired_nodes
            )
        self.changes[new.get(DIFF_ATTRIBUTE)] = command

        for nid, new_child in children_to_diff.items():
            self._diff_nodes(self.map_id_to_node_old[nid], new_child)

    # Methods that concern the building of the Odoo's xpath semantic tree
    def diff_xpath(self, old: etree._Element | str, new: etree._Element | str) -> str:
        changes = self.diff(old, new)
        all_removed = set()
        all_moved = set()

        # gather nodes that are moving around
        for change in changes.values():
            if "removed_nodes" in change:
                for rm_id in change["removed_nodes"]:
                    if rm_id not in all_moved:
                        all_removed.add(rm_id)
            if "acquired_nodes" in change:
                for moved_id in change["acquired_nodes"]:
                    all_removed.discard(moved_id)
                    all_moved.add(moved_id)

        delayed_removed = set()
        traversed = set()
        for nid in all_moved:
            node = self.map_id_to_node_old[nid]
            for ancestor in node.iterancestors(etree.Element):
                ancestor_id = ancestor.get(DIFF_ATTRIBUTE)
                if ancestor_id in traversed:
                    break
                else:
                    traversed.add(ancestor_id)
                if ancestor_id in all_removed:
                    delayed_removed.add(ancestor_id)
                    all_removed.discard(ancestor_id)
                    break

        diff_as_arch = etree.Element("data")
        for main_id, change in changes.items():
            if main_id in all_removed:
                continue
            # process changes: for changes that touch the children nodes:
            # apply the changes onto the old tree directly to have correct dynamic xpaths
            main_node = self.map_id_to_node_old[main_id]
            main_expr = self._get_xpath(main_node)
            xpath_changes = etree.Element("data")

            if change.get("replace_text"):
                self._handle_node_full_replace(main_id, main_expr, change, xpath_changes)
                diff_as_arch.append(xpath_changes)
                continue

            ## 1. Remove nodes first, that way browsing that subtree will be easier
            if change.get("removed_nodes"):
                for cnid in change["removed_nodes"]:
                    if cnid not in all_removed:
                        continue
                    rm_node = self.map_id_to_node_old[cnid]
                    expr = main_expr + self._get_node_xpath(rm_node)
                    xpath_rm = self._make_xpath_node(rm_node, position="replace", expr=expr)
                    xpath_changes.append(xpath_rm)
                    main_node.remove(rm_node)

            ## 2. Apply changes that touch the children: their order, the inner moves,
            ## the acquisition of nodes from outside (outer moves)
            holes = []
            if change.get("children_changes"):
                for children_change in change["children_changes"]:
                    target_node = self.map_id_to_node_old[children_change["target_id"]]
                    position = children_change["position"]
                    if position == "inside":
                        xpath_expr = main_expr
                    else:
                        xpath_expr = main_expr + self._get_node_xpath(target_node)

                    xpath_node = self._make_xpath_node(target_node, position=position, expr=xpath_expr)
                    if children_change["replace_text"]:
                        xpath_node.set("replace_text", "true")
                    has_changes = False
                    for leaf in children_change["leafs"]:
                        if leaf.get("ignore"):
                            continue
                        has_changes = True
                        if leaf["type"] == "text":
                            new_text = leaf["element"]
                            append_text(xpath_node, new_text)
                        else:
                            recompute_main_expr = False
                            if leaf.get("id"):
                                # If a leaf has an id its is one of two cases:
                                # 1. it is "owned": the leaf represents a node that was originally in the same parent
                                #   In this case, we don't need to compute the whole xpath for the node, we just need
                                #   to concatenate the parent's xpath with the current position of the node.
                                # 2. it is not "owned": the node comes from elsewhere in the tree, in this case we need
                                #   to compute the full node's xpath
                                to_apply_on_old = moved_node = self.map_id_to_node_old[leaf["id"]]
                                if leaf["owned"]:
                                    move_expr = main_expr + self._get_node_xpath(moved_node)
                                else:
                                    recompute_main_expr = int(leaf["id"]) < int(main_id)
                                    move_expr = self._get_xpath(moved_node)
                                to_push_in_xpath = self._make_xpath_node(moved_node, position="move", expr=move_expr)
                            else:
                                new_element = deepcopy(leaf["element"])
                                for new_node in self._visit_new_node_collect_holes(new_element):
                                    if new_node.tag == "o-diff-hole":
                                        holes.append(new_node)
                                    else:
                                        self._on_new_node(new_node)
                                to_apply_on_old = new_element
                                to_push_in_xpath = deepcopy(new_element)
                                to_push_in_xpath.tail = None

                            xpath_node.append(to_push_in_xpath)
                            if position == "inside":
                                target_node.append(to_apply_on_old)
                            elif position == "after":
                                target_node.addnext(to_apply_on_old)
                            elif position == "before":
                                target_node.addprevious(to_apply_on_old)

                            if recompute_main_expr:
                                main_expr = self._get_xpath(main_node)
                    if has_changes:
                        xpath_changes.append(xpath_node)

            ## Replace the holes that were made to move nodes into new elements
            self._handle_holes_replace(main_expr, holes, xpath_changes)

            ## 3. Make the changes onto the attributes. It is last because the node's identifiers
            ## and consequently the node's xpath may be affected
            if change["attributes"]:
                xpath_attrs = self._make_xpath_node(main_node, position="attributes", expr=main_expr)
                xpath_changes.append(xpath_attrs)
                for key, value in change["attributes"].items():
                    attr_node = etree.Element("attribute", name=key)
                    attr_node.text = value
                    xpath_attrs.append(attr_node)

            ## Only commit the changes into the result if there is something
            if len(xpath_changes) > 0:
                diff_as_arch.append(xpath_changes)

        if delayed_removed:
            delayed_data = etree.SubElement(diff_as_arch, "data")
            for rm_id in delayed_removed:
                node = self.map_id_to_node_old[rm_id]
                xpath_element = self._make_xpath_node(node, position="replace", expr=self._get_xpath(node))
                delayed_data.append(xpath_element)
                node.getparent().remove(node)

        indent_tree(diff_as_arch)
        return etree.tostring(diff_as_arch)

    def _get_identifiers(self, node):
        node_attrib = node.attrib
        identifiers = {}
        for attr in self.attributes_identifiers:
            if not attr in node_attrib:
                continue
            identifiers[attr] = node.get(attr)
        return identifiers

    def _get_descendants_axis_xpath(self, node: etree._Element, subtree: etree._Element | None = None) -> str:
        """Computes the xpath for `node` in terms of the descendants axis
        eg: [subtree]//[node's identification]
        If more than one node is found, the function returns an empty string

        subtree is a reference node for which we can compute the xpath separately
        """
        xpath_template = "//%s[@%s='%s']"
        if subtree is None:
            subtree = node.getroottree()
            is_subtree_element = False
        else:
            is_subtree_element = True

        tag = node.tag
        identifiers = self._get_identifiers(node)
        for name, value in identifiers.items():
            xpath_from_subtree = xpath_template % (tag, name, value)
            found = subtree.xpath("." + xpath_from_subtree)
            if found is not None and len(found) == 1:
                if is_subtree_element:
                    return self._get_xpath(subtree) + xpath_from_subtree
                return "." + xpath_from_subtree
        return ""

    def _get_children_axis_xpath(self, node: etree._Element, ancestors: list[etree._Element], subtree: etree._Element | None = None) -> str:
        """Computes the xpath of `node` in terms of direct children hierarchy
        eg: /form/div/notebook

        ancestors is in opposite order (bottom-up)
        subtree is a reference node for which we can compute the xpath separately
        """
        if subtree is not None:
            xpath = self._get_xpath(subtree)
        else:
            xpath = ""
        for node in chain(reversed(ancestors), [node]):
            xpath += self._get_node_xpath(node)
        return xpath

    def _get_subtree_and_ancestors(self, node: etree._Element) -> tuple[etree._Element | None, list[etree._Element]]:
        """For a node, returns its subtree parent (a relevant parent node that indicates a tree that could be separate)
        eg:
        <form> (this is a subtree)
            <div>
                <field> (this is a subtree)
                    <list> (this is a subtree)

        and its ancestors (excluding the subtree) in opposite order from the document's (ie bottom-up)
        """
        ancestors = []
        for ancestor in node.iterancestors(etree.Element):
            if self.is_subtree(ancestor):
                return ancestor, ancestors
            ancestors.append(ancestor)
        return None, ancestors

    def _get_node_xpath(self, node):
        """Computes the relative xpath of node in the context of its parent.
        Only the part concerning the location of the node inside the parent is returned
        eg: /field[@name='display_name'][1]
            /div[4]
        """
        identifiers = list(self._get_identifiers(node).items())
        main_identifier = identifiers and identifiers[0]

        iter_siblings = node.itersiblings(node.tag, preceding=True)
        if main_identifier:
            count = len([s for s in iter_siblings if s.get(main_identifier[0]) == main_identifier[1]])
        else:
            count = len(list(iter_siblings))
        count += 1  # As usual, xpath index starts at 1

        if main_identifier:
            local_xpath = f"/{node.tag}[@{main_identifier[0]}='{main_identifier[1]}']"
        else:
            local_xpath = f"/{node.tag}"

        if count > 1:
            local_xpath += f"[{count}]"

        return local_xpath

    def _get_xpath(self, node):
        subtree, ancestors = self._get_subtree_and_ancestors(node)
        absolute = self._get_descendants_axis_xpath(node, subtree)
        if absolute:
            return absolute
        return self._get_children_axis_xpath(node, ancestors, subtree)

    def _make_xpath_node(self, target_node, **kwargs):
        xpath_node = etree.Element("xpath", **kwargs)
        if target_node is None or not self.xpath_with_meta:
            return xpath_node
        for attr in target_node.attrib:
            if attr == DIFF_ATTRIBUTE:
                continue
            xpath_node.set(f"meta-{attr}", target_node.get(attr))
        return xpath_node

    def _handle_node_full_replace(self, node_id, node_expr, change, xpath_arch):
        main_node = self.map_id_to_node_old[node_id]
        new_node = change["new_node"]
        attribs = dict(new_node.attrib)
        if len(new_node) == 0:
            replace_with = etree.Element(main_node.tag, attribs)
            replace_with.text = new_node.text
            replace_xpath = self._make_xpath_node(main_node, position="replace", expr=self._get_xpath(main_node))
            replace_xpath.append(deepcopy(replace_with))
            xpath_arch.append(replace_xpath)
            main_node.getparent().replace(main_node, replace_with)
            self.map_id_to_node_old[node_id] = replace_with
            return

        # Append a temporary node inside the main one to store elements.
        # <oldnode>[*children]<tempnode /></oldnode>
        xpath_temp = self._make_xpath_node(main_node, position="inside", expr=node_expr)
        xpath_temp.append(etree.Element(main_node.tag, attribs))
        xpath_arch.append(xpath_temp)

        temp_node = etree.Element(main_node.tag, attribs)
        main_node.append(temp_node)

        inside_temp_xpath = self._make_xpath_node(None, expr=self._get_xpath(temp_node), position="inside")
        xpath_arch.append(inside_temp_xpath)

        holes = []
        for leaf in change["leafs"]:
            if leaf["type"] == "text":
                append_text(inside_temp_xpath, leaf["element"])
                continue
            recompute_main_expr = False
            if leaf.get("id"):
                # If a leaf has an id its is one of two cases:
                # 1. it is "owned": the leaf represents a node that was originally in the same parent
                #   In this case, we don't need to compute the whole xpath for the node, we just need
                #   to concatenate the parent's xpath with the current position of the node.
                # 2. it is not "owned": the node comes from elsewhere in the tree, in this case we need
                #   to compute the full node's xpath
                to_apply_on_old = moved_node = self.map_id_to_node_old[leaf["id"]]
                if leaf["owned"]:
                    move_expr = node_expr + self._get_node_xpath(moved_node)
                else:
                    recompute_main_expr = int(leaf["id"]) < int(node_id)
                    move_expr = self._get_xpath(moved_node)
                to_push_in_xpath = self._make_xpath_node(moved_node, position="move", expr=move_expr)
            else:
                new_element = deepcopy(leaf["element"])
                for new_node in self._visit_new_node_collect_holes(new_element):
                    if new_node.tag == "o-diff-hole":
                        holes.append(new_node)
                    else:
                        self._on_new_node(new_node)
                to_apply_on_old = new_element
                to_push_in_xpath = deepcopy(new_element)
                to_push_in_xpath.tail = None

            inside_temp_xpath.append(to_push_in_xpath)
            temp_node.append(to_apply_on_old)

            if recompute_main_expr:
                node_expr = self._get_xpath(main_node)

        self._handle_holes_replace(node_expr, holes, xpath_arch)

        # Replace the original node with the temporary one
        replace_with_temp = self._make_xpath_node(main_node, position="replace", expr=node_expr)
        replace_with_temp.append(self._make_xpath_node(temp_node, expr=self._get_xpath(temp_node), position="move"))
        xpath_arch.append(replace_with_temp)
        main_node.getparent().replace(main_node, temp_node)
        self.map_id_to_node_old[node_id] = temp_node

    def _handle_holes_replace(self, node_expr, holes, xpath_arch):
        for hole in holes:
            hole_id = hole.get("for")
            old_child = self.map_id_to_node_old[hole_id]
            move_to_expr = node_expr + "//o-diff-hole[@for='%s']" % hole_id
            move_to = self._make_xpath_node(None, expr=move_to_expr, position="replace")
            move_from_expr = self._get_xpath(old_child)
            move_from = self._make_xpath_node(old_child, position="move", expr=move_from_expr)
            move_to.append(move_from)
            xpath_arch.append(move_to)
            hole.getparent().replace(hole, old_child)

    def _visit_new_node(self, new_node):
        yield from visit(new_node, lambda n: not n.get(DIFF_ATTRIBUTE))

    def _visit_new_node_collect_holes(self, node):
        for node in self._visit_new_node(node):
            nid = node.get(DIFF_ATTRIBUTE)
            if nid:
                node.clear()
                node.tag = "o-diff-hole"
                node.set("for", nid)
            yield node

    def _on_new_node(self, node):
        return self.__on_new_node(node)
