# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .Link import Link
from .NodeWithChildren import NodeWithChildren


class LinkNode(NodeWithChildren):
    def __init__(self, get_node, options, tag, link_attribute, check_content=True, **kwargs):
        super().__init__(get_node, options, **kwargs)
        self.link_attribute = link_attribute
        self.check_content = check_content
        self.tag = tag
        self.default_label = "LINK"

    def _reduce(self, converter_state):
        merged_node = super()._reduce(converter_state)
        if not self.check_content or merged_node.content:
            target = self.node.get(self.link_attribute)
            if target is not None:
                link = Link(target, merged_node.content if self.check_content else self.default_label, self.tag)
                merged_node._content = link.key
                converter_state.add_link(link)
        return merged_node


class ANode(LinkNode):
    def __init__(self, get_node, options, **kwargs):
        super().__init__(get_node, options, "a", "href", **kwargs)


class ImgNode(LinkNode):
    def __init__(self, get_node, options, **kwargs):
        super().__init__(get_node, options, "img", "src", check_content=False, **kwargs)
        self.default_label = "Image"
