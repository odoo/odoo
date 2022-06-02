# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .NodeWithChildren import NodeWithChildren
from .constants import ALL_WHITESPACE


class InlineNode(NodeWithChildren):
    def __init__(self, get_node, options, element="", **kwargs):
        super().__init__(get_node, options, skip_whitespace_tails=False, **kwargs)
        self.fix = element

    def _get_child_prefix(self, child, position=0):
        """

        :param child: TextNode
        :param int position: Order of child element
        """
        return (self.fix if child.content and not ALL_WHITESPACE.match(child.content) else ""), True

    def _get_child_suffix(self, child):
        """

        :param child: TextNode
        """
        return self.fix if child.content and not ALL_WHITESPACE.match(child.content) else ""


class EmphasisNode(InlineNode):
    def __init__(self, get_node, options, **kwargs):
        super().__init__(get_node, options, element="*", **kwargs)


class BoldNode(InlineNode):
    def __init__(self, get_node, options, **kwargs):
        super().__init__(get_node, options, element="**", **kwargs)


class StrikeNode(InlineNode):
    def __init__(self, get_node, options, **kwargs):
        super().__init__(get_node, options, element="~~", **kwargs)
