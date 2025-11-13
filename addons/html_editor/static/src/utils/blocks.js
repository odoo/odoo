import { closestPath, findNode } from "./dom_traversal";

const blockTagNames = [
    "ADDRESS",
    "ARTICLE",
    "ASIDE",
    "BLOCKQUOTE",
    "DETAILS",
    "DIALOG",
    "DD",
    "DIV",
    "DL",
    "DT",
    "FIELDSET",
    "FIGCAPTION",
    "FIGURE",
    "FOOTER",
    "FORM",
    "H1",
    "H2",
    "H3",
    "H4",
    "H5",
    "H6",
    "HEADER",
    "HGROUP",
    "HR",
    "LI",
    "MAIN",
    "NAV",
    "OL",
    "P",
    "PRE",
    "SECTION",
    "TABLE",
    "UL",
    // The following elements are not in the W3C list, for some reason.
    "SELECT",
    "OPTION",
    "TR",
    "TD",
    "TBODY",
    "THEAD",
    "TH",
];

const computedStyleDisplayCache = new WeakMap();

/**
 * Return true if the given node is a block-level element, false otherwise.
 *
 * @param node
 */
export function isBlock(node) {
    if (!node || node.nodeType !== Node.ELEMENT_NODE) {
        return false;
    }
    const tagName = node.nodeName.toUpperCase();
    if (tagName === "BR") {
        // A <br> is always inline but getComputedStyle(br).display mistakenly
        // returns 'block' if its parent is display:flex (at least on Chrome and
        // Firefox (Linux)). Browsers normally support setting a <br>'s display
        // property to 'none' but any other change is not supported. Therefore
        // it is safe to simply declare that a <br> is never supposed to be a
        // block.
        return false;
    }
    // The node might not be in the DOM, in which case it has no CSS values.
    if (!node.isConnected) {
        return blockTagNames.includes(tagName);
    }
    // We won't call `getComputedStyle(node).display` more than once per node.
    let display = computedStyleDisplayCache.get(node);
    if (display === undefined) {
        const style = node.ownerDocument.defaultView.getComputedStyle(node);
        display = style.display;
        computedStyleDisplayCache.set(node, display);
    }
    if (display) {
        return !display.includes("inline") && display !== "contents";
    }
    return blockTagNames.includes(tagName);
}

export function closestBlock(node) {
    return findNode(closestPath(node), (node) => isBlock(node));
}
