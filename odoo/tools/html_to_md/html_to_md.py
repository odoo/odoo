# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import Union

import lxml

from .Converter import MarkdownConverter
from .EmptyNode import BrNode, HrNode
from .InlineNode import EmphasisNode, BoldNode, StrikeNode, InlineNode
from .LinkNode import ANode, ImgNode
from .ListNode import LiNode, OlNode, UlNode
from .NodeWithChildren import NodeWithChildren, BlockNode, PNode
from .TextNode import TextNode

TAG_TO_NODE_CLASS = {
    "hr": HrNode,
    "br": BrNode,
    "i": EmphasisNode,
    "em": EmphasisNode,
    "u": EmphasisNode,
    "b": BoldNode,
    "strong": BoldNode,
    "strike": StrikeNode,
    "del": StrikeNode,
    "p": PNode,
    "div": BlockNode,
    "span": InlineNode,
    "ol": OlNode,
    "ul": UlNode,
    "li": LiNode,
    "a": ANode,
    "img": ImgNode,
}


# noinspection PyProtectedMember
def get_converter(root_node: lxml.etree._Element) -> MarkdownConverter:
    return MarkdownConverter(root_node, get_node)


def get_node(tag: str, options, **kwargs) -> Union[NodeWithChildren, TextNode]:
    node_class = TAG_TO_NODE_CLASS.get(tag, NodeWithChildren)
    if tag == "img" and not options.get("keep_images"):
        node_class = NodeWithChildren
    return node_class(get_node, options, **kwargs)
