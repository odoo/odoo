import { childNodes, closestPath, findNode } from "./dom_traversal";

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
 * Return the computed `display` of the given element. We won't call
 * `getComputedStyle(node).display` more than once per node.
 *
 * @param {Element} node
 * @returns {string}
 */
function getComputedDisplay(node) {
    let display = computedStyleDisplayCache.get(node);
    if (display === undefined) {
        const style = (node.ownerDocument.defaultView ?? window).getComputedStyle(node);
        display = style.display;
        computedStyleDisplayCache.set(node, display);
    }
    return display;
}

// Inline displays whose inner display is `flow`: their content participates in
// the surrounding inline formatting context.
const flowInlineDisplays = new Set(["inline", "inline flow", "inline list-item"]);

/**
 * Return true if the given node is inline on the outside but lays out its
 * content independently on the inside (`inline-block`, `inline-flex`,
 * `inline-grid` and `inline-table`), meaning that content cannot affect the
 * whitespace or the line breaks around it.
 *
 * @param {Node} node
 * @returns {boolean}
 */
export function isInlineWithBlockFlowInside(node) {
    if (!node || node.nodeType !== Node.ELEMENT_NODE) {
        return false;
    }
    // A node that is not in the DOM has no CSS values: handle it as a regular
    // inline box.
    if (!node.isConnected) {
        return false;
    }
    const display = getComputedDisplay(node);
    if (!display || display === "none") {
        return false;
    }
    return display.startsWith("inline") && !flowInlineDisplays.has(display);
}

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
    const display = getComputedDisplay(node);
    // In case the node has display `contents`, its block status depends on its
    // children.
    if (display === "contents") {
        return childNodes(node).some((child) => isBlock(child));
    }
    // In case the node has display `none` we don't know what is its display
    // so we check its tagName in `blockTagNames`
    if (display && display !== "none") {
        return !display.includes("inline");
    }
    return blockTagNames.includes(tagName);
}

export function closestBlock(node) {
    return findNode(closestPath(node), (node) => isBlock(node));
}
