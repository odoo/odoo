# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

import lxml.etree

from .BaseNode import BaseNode
from .constants import BEFORE_EOL, INDENT
from .Link import Link
from .TextNode import merge_requirements, TextNode


class NodeWithChildren(BaseNode):
    """Composite node that is a parent for other nodes."""

    # Template-style configuration flags for subclasses
    ALWAYS_KEEP_ORIGINAL_WHITESPACE: bool = False
    CHILDREN_CANCEL_WHITESPACE: bool = False
    SKIP_WHITESPACE_IN_FIRST_CHILD: bool = False

    def __init__(
        self,
        get_node,
        options,
        element=None,
        **kwargs,
    ):
        self.keep_original_whitespace = kwargs.pop(
            "keep_original_whitespace",
            options.get("keep_original_whitespace", self.ALWAYS_KEEP_ORIGINAL_WHITESPACE)
        )
        super().__init__(get_node, options, **kwargs)
        self.element: lxml.etree._Element | None = element
        self._children: list[BaseNode] = []

        self._parse()

    def to_text_node(self, renderer_state):
        self._children = [child.to_text_node(renderer_state) for child in self._children]
        return self._reduce(renderer_state)

    def _parse(self):
        children_vals = {
            "indentation_level": self.indentation_level + 1 if self.induce_indent else self.indentation_level,
            "force_cancel_whitespace": self.CHILDREN_CANCEL_WHITESPACE,
            "position": 0,
        }

        if self.keep_original_whitespace:
            children_vals["keep_original_whitespace"] = True
        text_node_vals = children_vals | {"before_eol": self.options.get("before_eol")}

        if self.element.text and (not self.element.text.isspace() or self.keep_original_whitespace):
            child_node = TextNode.from_text(self.element.text, **text_node_vals)
            children_vals["position"] = self._add_child(child_node, children_vals["position"])

        for child_element in self.element:
            child_node = self.get_node(child_element.tag, self.options, element=child_element, **children_vals)
            children_vals["position"] = self._add_child(child_node, children_vals["position"])

            if effective_tail := child_node.get_effective_tail(child_element):
                child_node = TextNode.from_text(effective_tail, **text_node_vals)
                children_vals["position"] = self._add_child(child_node, children_vals["position"])

    def _add_child(self, child, current_position):
        self._children.append(child)
        return current_position + 1

    def _reduce(self, renderer_state):
        """Reduce all children to a single TextNode with appropriate prefixes/suffixes and spacing."""
        first_child = self._children[0] if self._children else None

        if not first_child:
            return TextNode.from_text("")

        # Update start requirements
        merged_node = first_child.to_text_node(renderer_state)
        first_child.starts_with_whitespace = not self.SKIP_WHITESPACE_IN_FIRST_CHILD and (
            self.starts_with_whitespace or merged_node.starts_with_whitespace
        )
        first_child.cancels_previous_whitespace = (
            merged_node.cancels_previous_whitespace
            or self.cancels_previous_whitespace
            or self.CHILDREN_CANCEL_WHITESPACE
        )
        first_child.require_before = merge_requirements(self.require_before, first_child.require_before)
        first_prefix, next_position = self._get_child_prefix(first_child, 0)
        first_child_suffix = self._get_child_suffix(first_child)
        merged_node.prepend(first_prefix)
        merged_node.append(first_child_suffix)

        # Add next children
        for next_sibling in self._children[1:]:
            next_text_node = next_sibling.to_text_node(renderer_state)
            prefix, _ = self._get_child_prefix(next_sibling, next_position)
            suffix = self._get_child_suffix(next_sibling)
            merged_node.concatenate(next_text_node, separator=prefix, suffix=suffix)

        merged_node.ends_with_whitespace = merged_node.ends_with_whitespace or self.ends_with_whitespace
        merged_node.require_after = merge_requirements(merged_node.require_after, self.require_after)

        if self.induce_indent and self.indentation_level:
            merged_node.induce_indent = True
            merged_node.prepend_lines(INDENT)
        return merged_node

    @staticmethod
    def _get_child_prefix(child: BaseNode, position: int = 0) -> tuple[str, bool]:
        """Provide child prefix and whether the next child should increment position."""
        return "", True

    @staticmethod
    def _get_child_suffix(child: BaseNode) -> str:
        """Generate suffix to add after child node content."""
        return ""

    # noinspection PyProtectedMember
    @staticmethod
    def get_effective_tail(element: lxml.etree._Element):
        """Return the effective tail from the node's _Element."""
        return element.tail if element.tail and not element.tail.isspace() else ""


class BlockNode(NodeWithChildren):
    DEFAULT_REQUIRE_BEFORE = "\n"
    SKIP_WHITESPACE_IN_FIRST_CHILD = True

    def _get_require_after(self, options: dict, require_after=None):
        return require_after if require_after is not None else options.get("before_eol", BEFORE_EOL) + "\n"


class PNode(BlockNode):
    def _get_require_after(self, options: dict, require_after=None):
        return "\n\n"


class PreNode(PNode):
    ALWAYS_KEEP_ORIGINAL_WHITESPACE = True


class HxNode(BlockNode):
    """Heading nodes"""

    MARKS = {"h1": "# ", "h2": "## ", "h3": "### ", "h4": "#### ", "h5": "##### ", "h6": "###### "}

    def __init__(self, tag, *args, **kwargs):
        mark = self.MARKS.get(tag, "# ")
        self.mark = mark
        super().__init__(*args, **kwargs)

    def _get_require_before(self, options: dict, require_before=None):
        return f"\n\n${self.mark}"

    def _get_require_after(self, options: dict, require_after=None):
        return "\n\n"

    def _get_child_prefix(self, child, position: int = 0) -> tuple[str, bool]:
        """Add an opening marker before non-whitespace child content."""
        return (self.mark if self._has_visible_content(child) else ""), True

    @staticmethod
    def _has_visible_content(child: BaseNode) -> bool:
        """Return True if the child is a TextNode with non-whitespace content."""
        return isinstance(child, TextNode) and child.content and not child.content.isspace()

    @staticmethod
    def get_effective_tail(element):
        """Strip whitespace at the end of the element's tail."""
        return (element.tail or "").lstrip()


class RootNode(NodeWithChildren):
    CHILDREN_CANCEL_WHITESPACE = True


class BlockquoteNode(NodeWithChildren):
    DEFAULT_REQUIRE_BEFORE = "\n"
    DEFAULT_REQUIRE_AFTER = "\n\n"
    DEFAULT_CANCELS_PREVIOUS_WHITESPACE = True

    def _reduce(self, renderer_state) -> str:
        md = super()._reduce(renderer_state)
        # Prefix each line with '> ' so nested blockquotes naturally become '> > ' etc.
        md.prepend_lines("> ")
        return md


class ListNode(NodeWithChildren):
    DEFAULT_CANCELS_PREVIOUS_WHITESPACE = True
    DEFAULT_INDUCE_INDENT = True

    def _get_require_before(self, options: dict, require_before=None):
        return "\n" if self.indentation_level else options.get("before_eol", BEFORE_EOL) + "\n"

    def _get_require_after(self, options: dict, require_after=None):
        return "\n" if self.indentation_level else "\n\n"


class LiNode(NodeWithChildren):
    DEFAULT_REQUIRE_BEFORE = "\n"
    DEFAULT_REQUIRE_AFTER = "\n"
    DEFAULT_CANCELS_PREVIOUS_WHITESPACE = True


class OlNode(ListNode):
    @staticmethod
    def _get_child_prefix(child, position=0):
        if not child.induce_indent:
            return f"{position + 1}. ", True
        return "", False


class UlNode(ListNode):
    @staticmethod
    def _get_child_prefix(child, position=0):
        if not child.induce_indent:
            return "* ", True
        return "", False


class TrNode(NodeWithChildren):
    DEFAULT_CANCELS_PREVIOUS_WHITESPACE = True
    DEFAULT_INDUCE_INDENT = False

    def _get_require_before(self, options: dict, require_after=None):
        return options.get("before_eol", BEFORE_EOL) + "\n"

    def _get_require_after(self, options: dict, require_after=None):
        return "\n"


class TdNode(NodeWithChildren):
    DEFAULT_REQUIRE_BEFORE = " "
    DEFAULT_REQUIRE_AFTER = ""
    DEFAULT_CANCELS_PREVIOUS_WHITESPACE = True


class EmptyNode(NodeWithChildren):
    """Base for leaf nodes that render fixed content with specific spaces."""

    CONTENT: str = ""

    DEFAULT_CANCELS_PREVIOUS_WHITESPACE = True
    DEFAULT_REQUIRE_AFTER = "\n"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._children.append(TextNode.from_text(self.CONTENT))

    @staticmethod
    def get_effective_tail(element):
        """Strip whitespace at the end of the element's tail."""
        return (element.tail or "").lstrip()


class HrNode(EmptyNode):
    """Horizontal rule."""

    CONTENT = "* * *"
    DEFAULT_REQUIRE_BEFORE = "\n"


class BrNode(EmptyNode):
    """Line break."""

    def _get_require_before(self, options, require_before=None):
        return options.get("before_eol", BEFORE_EOL)


class InlineNode(NodeWithChildren):
    """Support wrapping visible content with a marker (e.g., *, **, ~~)."""

    MARKS = {
        "b": "**",
        "em": "*",
        "del": "~~",
        "i": "*",
        "span": "",
        "strike": "~~",
        "strong": "**",
        "u": "*",
    }

    def __init__(self, *args, element=None, **kwargs):
        super().__init__(*args, element=element, **kwargs)
        self.mark = self.MARKS.get(element.tag, "") if element is not None else ""

    def _get_child_prefix(self, child, position: int = 0) -> tuple[str, bool]:
        """Add an opening marker before non-whitespace child content."""
        return (self.mark if self._has_visible_content(child) else ""), True

    def _get_child_suffix(self, child) -> str:
        """Add a closing marker after non-whitespace child content."""
        return self.mark if self._has_visible_content(child) else ""

    @staticmethod
    def _has_visible_content(child: BaseNode) -> bool:
        """Return True if the child is a TextNode with non-whitespace content."""
        return isinstance(child, TextNode) and child.content and not child.content.isspace()

    @staticmethod
    def get_effective_tail(element) -> str:
        """Return `element`'s raw tail if it exists or an empty string."""
        return element.tail or ""


class LinkNode(NodeWithChildren):
    CHECK_CONTENT: bool = True
    DEFAULT_LABEL: str = "LINK"
    LINK_ATTRIBUTE: str = None
    TAG: str = None

    def _reduce(self, renderer_state):
        merged_node = super()._reduce(renderer_state)
        target = self.element.get(self.LINK_ATTRIBUTE)
        if target and (label := self._get_label(merged_node.content, target)):
            link = Link(target, label, self.TAG)
            merged_node._content = link.key
            renderer_state.add_link(link)
        return merged_node

    def _get_label(self, content, target):
        return content if self.CHECK_CONTENT else self.DEFAULT_LABEL


class ANode(LinkNode):
    LINK_ATTRIBUTE: str = "href"
    TAG: str = "a"
    DEFAULT_REQUIRE_BEFORE = " "
    DEFAULT_CANCELS_PREVIOUS_WHITESPACE = True


class ImgNode(LinkNode):
    CHECK_CONTENT = False
    DEFAULT_LABEL = "Image"
    LINK_ATTRIBUTE = "src"
    TAG = "img"

    def _get_label(self, content, target):
        label_match = re.search(r'[^/]+(?=\.[a-zA-Z]+(?:\?|$))', target)
        return label_match[0] if label_match else self.DEFAULT_LABEL
