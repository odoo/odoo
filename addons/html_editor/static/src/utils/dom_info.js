import { closestBlock, isBlock } from "./blocks";
import { ancestors, closestElement, firstLeaf, lastLeaf } from "./dom_traversal";
import { DIRECTIONS, nodeSize } from "./position";

export function isEmpty(el) {
    const content = el.innerHTML.trim();
    if (content === "" || content === "<br>") {
        return true;
    }
    return false;
}

/**
 * Return true if the given node appears bold. The node is considered to appear
 * bold if its font weight is bigger than 500 (eg.: Heading 1), or if its font
 * weight is bigger than that of its closest block.
 *
 * @param {Node} node
 * @returns {boolean}
 */
export function isBold(node) {
    const fontWeight = +getComputedStyle(closestElement(node)).fontWeight;
    return fontWeight > 500 || fontWeight > +getComputedStyle(closestBlock(node)).fontWeight;
}

/**
 * Return true if the given node appears italic.
 *
 * @param {Node} node
 * @returns {boolean}
 */
export function isItalic(node) {
    return getComputedStyle(closestElement(node)).fontStyle === "italic";
}

/**
 * Return true if the given node appears underlined.
 *
 * @param {Node} node
 * @returns {boolean}
 */
export function isUnderline(node) {
    let parent = closestElement(node);
    while (parent) {
        if (getComputedStyle(parent).textDecorationLine.includes("underline")) {
            return true;
        }
        parent = parent.parentElement;
    }
    return false;
}

/**
 * Return true if the given node appears struck through.
 *
 * @param {Node} node
 * @returns {boolean}
 */
export function isStrikeThrough(node) {
    let parent = closestElement(node);
    while (parent) {
        if (getComputedStyle(parent).textDecorationLine.includes("line-through")) {
            return true;
        }
        parent = parent.parentElement;
    }
    return false;
}

/**
 * Return true if the given node font-size is equal to `props.size`.
 *
 * @param {Object} props
 * @param {Node} props.node A node to compare the font-size against.
 * @param {String} props.size The font-size value of the node that will be
 *     checked against.
 * @returns {boolean}
 */
export function isFontSize(node, props) {
    const element = closestElement(node);
    return getComputedStyle(element)["font-size"] === props.size;
}

/**
 * Return true if the given node classlist contains `props.className`.
 *
 * @param {Object} props
 * @param {Node} node A node to compare the font-size against.
 * @param {String} props.className The name of the class.
 * @returns {boolean}
 */
export function hasClass(node, props) {
    const element = closestElement(node);
    return element.classList.contains(props.className);
}

/**
 * Return true if the given node appears in a different direction than that of
 * the editable ('ltr' or 'rtl').
 *
 * Note: The direction of the editable is set on its "dir" attribute, to the
 * value of the "direction" option on instantiation of the editor.
 *
 * @param {Node} node
 * @param {Element} editable
 * @returns {boolean}
 */
export function isDirectionSwitched(node, editable) {
    const defaultDirection = editable.getAttribute("dir") || "ltr";
    return getComputedStyle(closestElement(node)).direction !== defaultDirection;
}

// /**
//  * Return true if the given node is a row element.
//  */
export function isRow(node) {
    return ["TH", "TD"].includes(node.tagName);
}

export function isZWS(node) {
    return node && node.textContent === "\u200B";
}

/**
 * Returns true if the given node is in a PRE context for whitespace handling.
 *
 * @param {Node} node
 * @returns {boolean}
 */
export function isInPre(node) {
    const element = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
    return (
        !!element &&
        (!!element.closest("pre") ||
            getComputedStyle(element).getPropertyValue("white-space") === "pre")
    );
}

export const whitespace = `[^\\S\\u00A0\\u0009]`; // for formatting (no "real" content) (TODO: 0009 shouldn't be included)
const whitespaceRegex = new RegExp(`^${whitespace}*$`);
export function isWhitespace(value) {
    const str = typeof value === "string" ? value : value.nodeValue;
    return whitespaceRegex.test(str);
}

// eslint-disable-next-line no-control-regex
const visibleCharRegex = /[^\s\u200b]|[\u00A0\u0009]$/; // contains at least a char that is always visible (TODO: 0009 shouldn't be included)
export function isVisibleTextNode(testedNode) {
    if (!testedNode || !testedNode.length || testedNode.nodeType !== Node.TEXT_NODE) {
        return false;
    }
    if (
        visibleCharRegex.test(testedNode.textContent) ||
        (isInPre(testedNode) && isWhitespace(testedNode))
    ) {
        return true;
    }
    if (testedNode.textContent === "\u200B") {
        return false;
    }
    // The following assumes node is made entirely of whitespace and is not
    // preceded of followed by a block.
    // Find out contiguous preceding and following text nodes
    let preceding;
    let following;
    // Control variable to know whether the current node has been found
    let foundTestedNode;
    const currentNodeParentBlock = closestBlock(testedNode);
    if (!currentNodeParentBlock) {
        return false;
    }
    const nodeIterator = document.createNodeIterator(currentNodeParentBlock);
    for (let node = nodeIterator.nextNode(); node; node = nodeIterator.nextNode()) {
        if (node.nodeType === Node.TEXT_NODE) {
            // If we already found the tested node, the current node is the
            // contiguous following, and we can stop looping
            // If the current node is the tested node, mark it as found and
            // continue.
            // If we haven't reached the tested node, overwrite the preceding
            // node.
            if (foundTestedNode) {
                following = node;
                break;
            } else if (testedNode === node) {
                foundTestedNode = true;
            } else {
                preceding = node;
            }
        } else if (isBlock(node)) {
            // If we found the tested node, then the following node is irrelevant
            // If we didn't, then the current preceding node is irrelevant
            if (foundTestedNode) {
                break;
            } else {
                preceding = null;
            }
        } else if (foundTestedNode && !isWhitespace(node)) {
            // <block>space<inline>text</inline></block> -> space is visible
            following = node;
            break;
        }
    }
    while (following && !visibleCharRegex.test(following.textContent)) {
        following = following.nextSibling;
    }
    // Missing preceding or following: invisible.
    // Preceding or following not in the same block as tested node: invisible.
    if (
        !(preceding && following) ||
        currentNodeParentBlock !== closestBlock(preceding) ||
        currentNodeParentBlock !== closestBlock(following)
    ) {
        return false;
    }
    // Preceding is whitespace or following is whitespace: invisible
    return visibleCharRegex.test(preceding.textContent);
}

/**
 * Returns whether the given node is a element that could be considered to be
 * removed by itself = self closing tags.
 *
 * @param {Node} node
 * @returns {boolean}
 */
const selfClosingElementTags = ["BR", "IMG", "INPUT"];
export function isSelfClosingElement(node) {
    return node && selfClosingElementTags.includes(node.nodeName);
}

/**
 * Returns whether removing the given node from the DOM will have a visible
 * effect or not.
 *
 * Note: TODO this is not handling all cases right now, just the ones the
 * caller needs at the moment. For example a space text node between two inlines
 * will always return 'true' while it is sometimes invisible.
 *
 * @param {Node} node
 * @returns {boolean}
 */
export function isVisible(node) {
    return (
        !!node &&
        ((node.nodeType === Node.TEXT_NODE && isVisibleTextNode(node)) ||
            isSelfClosingElement(node) ||
            hasVisibleContent(node))
    );
}
export function hasVisibleContent(node) {
    return [...(node?.childNodes || [])].some((n) => isVisible(n));
}

export const isNotEditableNode = (node) =>
    node.getAttribute &&
    node.getAttribute("contenteditable") &&
    node.getAttribute("contenteditable").toLowerCase() === "false";

export function isUnbreakable(node) {
    if (!node || node.nodeType === Node.TEXT_NODE) {
        return false;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) {
        return true;
    }
    return (
        isUnremovable(node) || // An unremovable node is always unbreakable.
        // @todo @phoenix: move the specific part in a proper plugin.
        ["TABLE", "THEAD", "TBODY", "TFOOT", "TR", "TH", "TD", "SECTION", "DIV"].includes(
            node.tagName
        ) ||
        node.hasAttribute("t") ||
        (node.nodeType === Node.ELEMENT_NODE &&
            (node.nodeName === "T" ||
                node.getAttribute("t-if") ||
                node.getAttribute("t-esc") ||
                node.getAttribute("t-elif") ||
                node.getAttribute("t-else") ||
                node.getAttribute("t-foreach") ||
                node.getAttribute("t-value") ||
                node.getAttribute("t-out") ||
                node.getAttribute("t-raw"))) ||
        node.getAttribute("t-field") ||
        node.classList.contains("oe_unbreakable")
    );
}

// @todo @phoenix: adapt .oid parts
export function isUnremovable(node) {
    return (
        (node.nodeType !== Node.ELEMENT_NODE && node.nodeType !== Node.TEXT_NODE) ||
        node.oid === "root" ||
        // @todo @phoenix: move the specific part in a proper plugin.
        (node.nodeType === Node.ELEMENT_NODE &&
            (node.classList.contains("o_editable") ||
                node.getAttribute("t-set") ||
                node.getAttribute("t-call"))) ||
        (node.classList && node.classList.contains("oe_unremovable")) ||
        (node.nodeName === "SPAN" &&
            node.parentElement &&
            node.parentElement.getAttribute("data-oe-type") === "monetary") ||
        (node.ownerDocument &&
            node.ownerDocument.defaultWindow &&
            !ancestors(node).find((ancestor) => ancestor.oid === "root")) // Node is in DOM but not in editable.
    );
}

const iconTags = ["I", "SPAN"];
// @todo @phoenix: move the specific part in a proper plugin.
const iconClasses = ["fa", "fab", "fad", "far", "oi"];

export const ICON_SELECTOR = iconTags
    .map((tag) => {
        return iconClasses
            .map((cls) => {
                return `${tag}.${cls}`;
            })
            .join(", ");
    })
    .join(", ");

/**
 * Indicates if the given node is an icon element.
 *
 * @see ICON_SELECTOR
 * @param {?Node} [node]
 * @returns {boolean}
 */
export function isIconElement(node) {
    return !!(
        node &&
        iconTags.includes(node.nodeName) &&
        iconClasses.some((cls) => node.classList.contains(cls))
    );
}
// @todo @phoenix: move the specific part in a proper plugin.
export function isMediaElement(node) {
    return (
        isIconElement(node) ||
        (node.classList &&
            (node.classList.contains("o_image") || node.classList.contains("media_iframe_video")))
    );
}

/**
 * A "protected" node will have its mutations filtered and not be registered
 * in an history step. Some editor features like selection handling, command
 * hint, toolbar, tooltip, etc. are also disabled. Protected roots have their
 * data-oe-protected attribute set to either "" or "true". If the closest parent
 * with a data-oe-protected attribute has the value "false", it is not
 * protected. Unknown values are ignored.
 *
 * @param {Node} node
 * @returns {boolean}
 */
export function isProtected(node) {
    const closestProtectedElement = closestElement(node, "[data-oe-protected]");
    if (closestProtectedElement) {
        return ["", "true"].includes(closestProtectedElement.dataset.oeProtected);
    }
    return false;
}

// This is a list of "paragraph-related elements", defined as elements that
// behave like paragraphs.
export const paragraphRelatedElements = [
    "P",
    "H1",
    "H2",
    "H3",
    "H4",
    "H5",
    "H6",
    "PRE",
    "BLOCKQUOTE",
];

/**
 * Return true if the given node allows "paragraph-related elements".
 *
 * @see paragraphRelatedElements
 * @param {Node} node
 * @returns {boolean}
 */
export function allowsParagraphRelatedElements(node) {
    return isBlock(node) && !paragraphRelatedElements.includes(node.nodeName);
}

/**
 * Checks whether or not the given block has any visible content, except for
 * a placeholder BR.
 *
 * @param {HTMLElement} blockEl
 * @returns {boolean}
 */
export function isEmptyBlock(blockEl) {
    if (!blockEl || blockEl.nodeType !== Node.ELEMENT_NODE) {
        return false;
    }
    if (visibleCharRegex.test(blockEl.textContent)) {
        return false;
    }
    if (blockEl.querySelectorAll("br").length >= 2) {
        return false;
    }
    const nodes = blockEl.querySelectorAll("*");
    for (const node of nodes) {
        // There is no text and no double BR, the only thing that could make
        // this visible is a "visible empty" node like an image.
        if (node.nodeName != "BR" && (isSelfClosingElement(node) || isIconElement(node))) {
            return false;
        }
    }
    return true;
}
/**
 * Checks whether or not the given block element has something to make it have
 * a visible height (except for padding / border).
 *
 * @param {HTMLElement} blockEl
 * @returns {boolean}
 */
export function isShrunkBlock(blockEl) {
    return isEmptyBlock(blockEl) && !blockEl.querySelector("br") && blockEl.nodeName !== "IMG";
}

export function isEditorTab(node) {
    return node && node.nodeName === "SPAN" && node.classList.contains("oe-tabs");
}

export function getDeepestPosition(node, offset) {
    let direction = DIRECTIONS.RIGHT;
    let next = node;
    while (next) {
        if (
            (isVisible(next) && (!isBlock(next) || next.isContentEditable)) ||
            (isZWS(next) && closestElement(next).isContentEditable)
        ) {
            // Valid node: update position then try to go deeper.
            if (next !== node) {
                [node, offset] = [next, direction ? 0 : nodeSize(next)];
            }
            // First switch direction to left if offset is at the end.
            direction = offset < node.childNodes.length;
            next = node.childNodes[direction ? offset : offset - 1];
        } else if (direction && next.nextSibling) {
            // Invalid node: skip to next sibling (without crossing blocks).
            next = next.nextSibling;
        } else {
            // Invalid node: skip to previous sibling (without crossing blocks).
            direction = DIRECTIONS.LEFT;
            next = !isBlock(next.previousSibling) && next.previousSibling;
        }
        // Avoid too-deep ranges inside self-closing elements like [BR, 0].
        next = !isSelfClosingElement(next) && next;
    }
    return [node, offset];
}

export function previousLeaf(node, editable, skipInvisible = false) {
    let ancestor = node;
    while (ancestor && !ancestor.previousSibling && ancestor !== editable) {
        ancestor = ancestor.parentElement;
    }
    if (ancestor && ancestor !== editable) {
        if (skipInvisible && !isVisible(ancestor.previousSibling)) {
            return previousLeaf(ancestor.previousSibling, editable, skipInvisible);
        } else {
            const last = lastLeaf(ancestor.previousSibling);
            if (skipInvisible && !isVisible(last)) {
                return previousLeaf(last, editable, skipInvisible);
            } else {
                return last;
            }
        }
    }
}
export function nextLeaf(node, editable, skipInvisible = false) {
    let ancestor = node;
    while (ancestor && !ancestor.nextSibling && ancestor !== editable) {
        ancestor = ancestor.parentElement;
    }
    if (ancestor && ancestor !== editable) {
        if (skipInvisible && ancestor.nextSibling && !isVisible(ancestor.nextSibling)) {
            return nextLeaf(ancestor.nextSibling, editable, skipInvisible);
        } else {
            const first = firstLeaf(ancestor.nextSibling);
            if (skipInvisible && !isVisible(first)) {
                return nextLeaf(first, editable, skipInvisible);
            } else {
                return first;
            }
        }
    }
}

function hasPseudoElementContent(node, pseudoSelector) {
    const content = getComputedStyle(node, pseudoSelector).getPropertyValue("content");
    return content && content !== "none";
}

const NOT_A_NUMBER = /[^\d]/g;

export function areSimilarElements(node, node2) {
    if (![node, node2].every((n) => n?.nodeType === Node.ELEMENT_NODE)) {
        return false; // The nodes don't both exist or aren't both elements.
    }
    if (node.nodeName !== node2.nodeName) {
        return false; // The nodes aren't the same type of element.
    }
    const nodeName = node.nodeName;

    for (const name of new Set([...node.getAttributeNames(), ...node2.getAttributeNames()])) {
        if (node.getAttribute(name) !== node2.getAttribute(name)) {
            return false; // The nodes don't have the same attributes.
        }
    }
    if (
        [node, node2].some(
            (n) => hasPseudoElementContent(n, ":before") || hasPseudoElementContent(n, ":after")
        )
    ) {
        return false; // The nodes have pseudo elements with content.
    }
    if (isIconElement(node) || isIconElement(node2)) {
        return false;
    }
    if (["UL", "OL"].includes(nodeName)) {
        return !isSelfClosingElement(node) && !isSelfClosingElement(node2); // The nodes are non-empty lists. TODO: this doesn't check that and it will always be true!
    }
    if (isBlock(node) || isSelfClosingElement(node) || isSelfClosingElement(node2)) {
        return false; // The nodes are blocks or are empty but visible. TODO: Not sure this was what we wanted to check (see just above).
    }
    const nodeStyle = getComputedStyle(node);
    const node2Style = getComputedStyle(node2);
    return (
        !+nodeStyle.padding.replace(NOT_A_NUMBER, "") &&
        !+node2Style.padding.replace(NOT_A_NUMBER, "") &&
        !+nodeStyle.margin.replace(NOT_A_NUMBER, "") &&
        !+node2Style.margin.replace(NOT_A_NUMBER, "")
    );
}
