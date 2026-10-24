import base64
from urllib.parse import unquote


def process_xop(document, message_pack):
    """Iterate through the tree and replace the xop:include elements."""

    xop_nodes = document.xpath(
        "//xop:Include", namespaces={"xop": "http://www.w3.org/2004/08/xop/include"}
    )
    num_replaced = 0

    for xop_node in xop_nodes:
        href = xop_node.get("href")
        if href.startswith("cid:"):
            # URL can be encoded. RFC2392
            href = "<%s>" % unquote(href[4:])

        value = message_pack.get_by_content_id(href)
        if not value:
            raise ValueError("No part found for: %r" % xop_node.get("href"))
        num_replaced += 1

        xop_parent = xop_node.getparent()
        xop_parent.remove(xop_node)
        xop_parent.text = base64.b64encode(value.content)

    return num_replaced > 0
