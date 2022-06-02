# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from functools import partial

from .NodeWithChildren import (
    ANode,
    BlockNode,
    BlockquoteNode,
    BrNode,
    HrNode,
    HxNode,
    ImgNode,
    InlineNode,
    LiNode,
    NodeWithChildren,
    OlNode,
    PNode,
    PreNode,
    TdNode,
    TrNode,
    UlNode,
)
from .PlaintextTree import PlaintextTree

_logger = logging.getLogger(__name__)

HxTAGS = [f"h{level}" for level in range(1, 7)]
INLINE_TAGS = ["b", "del", "em", "i", "span", "strike", "strong", "u"]

TAG_TO_NODE_CLASS = (
    {
        "a": ANode,
        "blockquote": BlockquoteNode,
        "br": BrNode,
        "code": PNode,
        "div": BlockNode,
        "hr": HrNode,
        "img": ImgNode,
        "li": LiNode,
        "marquee": BlockNode,
        "ol": OlNode,
        "p": PNode,
        "pre": PreNode,
        "table": NodeWithChildren,
        "td": TdNode,
        "th": TdNode,
        "tr": TrNode,
        "ul": UlNode,
    }
    | {title_tag: partial(HxNode, title_tag) for title_tag in HxTAGS}
    | {inline_tag: InlineNode for inline_tag in INLINE_TAGS}
)


def html_to_plaintext(root, **options):
    """Convert an HTML tree into Markdown.

    Unless configured otherwise in `options`, the following rules are applied:
      * images are included (prevent with strip_images=True)
      * links are included (prevent with strip_links=True)
      * links are rendered as footnotes (switch to inline with inline_links=True)
    with inline reference.
      * newlines are reduced as in HTML rendering (prevent keep_original_whitespace=True)

    :param lxml.etree._Element._Element root: The root node of the parsed HTML tree.
    :param options: Options to pass to the renderer.
    """
    return PlaintextTree(root, get_node).render_plaintext(options=options)


def get_node(tag: str, options, **kwargs):
    """Get Node instance for node tag.

    :rtype: NodeWithChildren | TextNode
    """
    node_class = TAG_TO_NODE_CLASS.get(tag)
    if not node_class:
        _logger.debug("html_to_plaintext: no match found for tag %s, using base NodeWithChildren", tag)
        node_class = NodeWithChildren
    elif tag == "img" and (options.get("strip_images") or options.get("strip_links")):
        node_class = NodeWithChildren
    elif tag == "a" and options.get("strip_links"):
        node_class = InlineNode
    return node_class(get_node, options, **kwargs)
