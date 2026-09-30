export function escapeTextNodes(el) {
    const nodeFilter = (node) => {
        if (
            node.nodeType === Node.ELEMENT_NODE &&
            (node.matches("object,iframe,script,style") ||
                (node.hasAttribute("data-oe-model") &&
                    node.getAttribute("data-oe-model") !== "ir.ui.view"))
        ) {
            return NodeFilter.FILTER_REJECT; // Skip this node and its descendants
        }
        if (node.nodeType === Node.TEXT_NODE) {
            return NodeFilter.FILTER_ACCEPT;
        }
        return NodeFilter.FILTER_SKIP; // Skip other nodes, but visit their children
    };
    if (nodeFilter(el) === NodeFilter.FILTER_REJECT) {
        return;
    }
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_ALL, nodeFilter);
    const escaper = document.createElement("div");
    let node;
    while ((node = walker.nextNode())) {
        escaper.textContent = node.nodeValue;
        node.nodeValue = escaper.innerHTML;
    }
}
