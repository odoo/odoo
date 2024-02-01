# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .NodeWithChildren import NodeWithChildren
from .TextNode import text_to_text_node
from .constants import LINE_ENDING


class EmptyNode(NodeWithChildren):
    def __init__(self, get_node, options, content, **kwargs):
        super().__init__(
            get_node, options, cancels_previous_whitespace=True, cancels_leading_tail_whitespace=True, **kwargs
        )
        self._children.append(text_to_text_node(content, verbose=self.verbose))


class HrNode(EmptyNode):
    def __init__(self, get_node, options, **kwargs):
        super().__init__(get_node, options, content="---", require_before="\n", require_after="\n", **kwargs)


class BrNode(EmptyNode):
    def __init__(self, get_node, options, **kwargs):
        super().__init__(
            get_node,
            options,
            content="",
            require_before=options.get("line_ending", LINE_ENDING),
            require_after="\n",
            **kwargs,
        )
