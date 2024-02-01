# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import Optional

import lxml.etree

from .BaseNode import BaseNode
from .TextNode import merge_required, text_to_text_node
from .constants import ALL_WHITESPACE, INDENT, LINE_ENDING


class NodeWithChildren(BaseNode):
    # noinspection PyProtectedMember
    def __init__(
        self,
        get_node,
        options,
        node=None,
        skip_whitespace_in_first_child: bool = False,
        skip_whitespace_tails: bool = True,
        children_cancel_whitespace: bool = False,
        **kwargs,
    ):
        super().__init__(get_node, options, **kwargs)
        self.node: Optional[lxml.etree._Element] = node
        self.skip_whitespace_tails = skip_whitespace_tails
        self.skip_whitespace_in_first_child = skip_whitespace_in_first_child
        self.children_cancel_whitespace = children_cancel_whitespace
        self._children: list[BaseNode] = []

        self._make_children()

    def get_str_components(self):
        components = super().get_str_components()
        components.update(
            node_tag=self.node.tag if self.node is not None else None,
            children=[child.get_str_components() for child in self._children],
        )
        return components

    def _make_children(self):
        if self.verbose:
            print(f"shaping node {self.node} {self.node.text if self.node is not None else ''}")

        common_child_values = dict(
            verbose=self.verbose,
            indentation_level=self.indentation_level + 1 if self.induce_indent else self.indentation_level,
            force_cancel_whitespace=self.children_cancel_whitespace,
        )
        next_position = 0

        if self.node.text and not ALL_WHITESPACE.match(self.node.text):
            child = text_to_text_node(self.node.text, **common_child_values)
            next_position = self._add_child(child, next_position)

        for child_node in self.node:
            child = self.get_node(
                child_node.tag, self.options, node=child_node, position=next_position, **common_child_values
            )
            next_position = self._add_child(child, next_position)

            if child_node.tail and (not self.skip_whitespace_tails or not ALL_WHITESPACE.match(child_node.tail)):
                content = child_node.tail if not child.cancels_leading_tail_whitespace else child_node.tail.lstrip()
                child = text_to_text_node(content, position=next_position, **common_child_values)
                next_position = self._add_child(child, next_position)

    def _add_child(self, child, current_position):
        self._children.append(child)
        return current_position + 1

    def _reduce(self, converter_state):
        first_child = self._children[0] if self._children else None

        if not first_child:
            return text_to_text_node("")

        merged_node = first_child.to_text_node(converter_state)

        self._merge_start_requirements(first_child, merged_node)

        first_prefix, next_position = self._get_child_prefix(first_child, 0)
        first_child_suffix = self._get_child_suffix(first_child)
        merged_node.prepend(first_prefix)
        merged_node.append(first_child_suffix)

        if self.verbose:
            print("First child to text: ", merged_node)

        for next_sibling in self._children[1:]:
            self._merge_next_child(next_sibling, converter_state, merged_node, next_position)
            if self.verbose:
                print("After additional node", merged_node)

        merged_node.ends_with_whitespace = merged_node.ends_with_whitespace or self.ends_with_whitespace
        merged_node.require_after = merge_required(merged_node.require_after, self.require_after)

        if self.induce_indent and self.indentation_level:
            merged_node.induce_indent = True
            merged_node.prepend_lines(INDENT)
        return merged_node

    def _merge_start_requirements(self, merged_node, first_child):
        merged_node.starts_with_whitespace = not self.skip_whitespace_in_first_child and (
            self.starts_with_whitespace or first_child.starts_with_whitespace
        )
        merged_node.cancels_previous_whitespace = (
            first_child.cancels_previous_whitespace
            or self.cancels_previous_whitespace
            or self.children_cancel_whitespace
        )
        merged_node.require_before = merge_required(self.require_before, merged_node.require_before)

    def _merge_next_child(self, next_child, converter_state, merged_node, prefixed_position):
        next_text_node = next_child.to_text_node(converter_state)
        prefix, _ = self._get_child_prefix(next_child, prefixed_position)
        suffix = self._get_child_suffix(next_child)
        merged_node.concatenate(next_text_node, separator=prefix, suffix=suffix)

    @staticmethod
    def _get_child_prefix(child, position=0) -> (str, bool):
        """Provide child prefix and position to assign next child.

        `Prefix` should be added before child text node content,
        `position` to assign the following child is used in overrides,
        namely <Ol> to skip incrementing the prefix.
        """
        return "", True

    @staticmethod
    def _get_child_suffix(child) -> str:
        """Generate suffix to add after child node content."""
        return ""

    def to_markdown(self, converter_state) -> str:
        text_node = self.to_text_node(converter_state)
        return text_node.content

    def to_text_node(self, converter_state):
        self._children = [child.to_text_node(converter_state) for child in self._children]
        return self._reduce(converter_state)


class BlockNode(NodeWithChildren):
    def __init__(self, get_node, options, **kwargs):
        super().__init__(
            get_node,
            options,
            require_before="\n",
            require_after=kwargs.pop("require_after", options.get("line_ending", LINE_ENDING) + "\n"),
            skip_whitespace_in_first_child=True,
            **kwargs,
        )


class PNode(BlockNode):
    def __init__(self, get_node, options, **kwargs):
        super().__init__(get_node, options, require_after="\n\n", **kwargs)


class RootNode(NodeWithChildren):
    def __init__(self, get_node, options, node, verbose):
        super().__init__(
            get_node, options, node, verbose=verbose, children_cancel_whitespace=True, skip_whitespace_tails=True
        )
