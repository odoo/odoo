# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .NodeWithChildren import NodeWithChildren
from .constants import LINE_ENDING


class ListNode(NodeWithChildren):
    def __init__(self, get_node, options, **kwargs):
        super().__init__(
            get_node,
            options,
            skip_whitespace_tails=True,
            require_after="\n" if kwargs.get("indentation_level", False) else "\n\n",
            require_before="\n"
            if kwargs.get("indentation_level", False)
            else options.get("line_ending", LINE_ENDING) + "\n",
            induce_indent=True,
            cancels_previous_whitespace=True,
            **kwargs,
        )


class LiNode(NodeWithChildren):
    def __init__(self, get_node, options, **kwargs):
        super().__init__(
            get_node,
            options,
            require_before="\n",
            require_after="\n",
            cancels_previous_whitespace=True,
            **kwargs,
        )


class OlNode(ListNode):
    @staticmethod
    def _get_child_prefix(child, position=0):
        if not child.induce_indent:
            return f"{position+1}. ", True
        return "", False


class UlNode(ListNode):
    @staticmethod
    def _get_child_prefix(child, position=0):
        if not child.induce_indent:
            return "* ", True
        return "", False
