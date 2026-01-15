import { baseContainerGlobalSelector } from "./base_container";
import { closestBlock, isBlock } from "./blocks";
import { childNodes, closestElement, firstLeaf, lastLeaf } from "./dom_traversal";
import { DIRECTIONS, nodeSize } from "./position";

export function isEmpty(el) {
    if (isProtecting(el) || isProtected(el)) {
        return false;
    }
    const content = el.innerHTML.trim();
    if (content === "" || content === "<br>") {
        return true;
    }
    return false;
}

export function isEmptyTextNode(node) {
    if (node.nodeType !== Node.TEXT_NODE) {
        return false;
    }
    if (!node.textContent) {
        return true;
    }
    const trimmedContent = node.textContent.trim();
    if (!trimmedContent) {
        // Only `\n` is considered as empty
        if (node.textContent.includes("\n")) {
            return true;
        }
        // Only spaces is not considered as empty
        // we technically can apply styles on spaces
        if (node.textContent) {
            return false;
        }
    }
    return !trimmedContent;
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
    const referenceElement = closestElement(
        node,
        (el) => isBlock(el) || +getComputedStyle(el).fontWeight !== fontWeight
    );
    return fontWeight > 500 || fontWeight > +getComputedStyle(referenceElement).fontWeight;
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
        if (
            !parent.classList.contains("o_checked") &&
            getComputedStyle(parent).textDecorationLine.includes("line-through")
        ) {
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

export const ZERO_WIDTH_CHARS = ["\u200b", "\ufeff"];

export const whitespace = `[^\\S\\u00A0\\u0009\\ufeff]`; // for formatting (no "real" content) (TODO: 0009 shouldn't be included)
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
    if (isProtected(testedNode)) {
        return true;
    }
    if (
        visibleCharRegex.test(testedNode.textContent) ||
        (isInPre(testedNode) && isWhitespace(testedNode))
    ) {
        return true;
    }
    if (ZERO_WIDTH_CHARS.includes(testedNode.textContent)) {
        return false; // a ZW(NB)SP is always invisible, regardless of context.
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
const selfClosingElementTags = ["BR", "IMG", "INPUT", "T", "HR"];
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
            // @todo: handle it in resources?
            isMediaElement(node) ||
            hasVisibleContent(node) ||
            isProtecting(node) ||
            isEmbeddedComponent(node))
    );
}
export function hasVisibleContent(node) {
    return (node ? childNodes(node) : []).some((n) => isVisible(n));
}

export function isButton(node) {
    if (!node || node.nodeType !== Node.ELEMENT_NODE) {
        return false;
    }
    return node.nodeName === "BUTTON" || node.classList.contains("btn");
}

export function isZwnbsp(node) {
    return node?.nodeType === Node.TEXT_NODE && node.textContent === "\ufeff";
}

export function isTangible(node) {
    return isVisible(node) || isZwnbsp(node) || hasTangibleContent(node);
}

export function hasTangibleContent(node) {
    return (node ? childNodes(node) : []).some((n) => isTangible(n));
}

export const isNotEditableNode = (node) =>
    node.getAttribute &&
    node.getAttribute("contenteditable") &&
    node.getAttribute("contenteditable").toLowerCase() === "false";

const iconTags = ["I", "SPAN"];
// @todo @phoenix: move the specific part in a proper plugin.
export const iconClasses = ["fa", "fab", "fad", "far", "oi"];

export const ICON_SELECTOR = iconTags
    .map((tag) => iconClasses.map((cls) => `${tag}.${cls}`).join(", "))
    .join(", ");

export const MEDIA_SELECTOR = `${ICON_SELECTOR} , .o_image, .media_iframe_video`;

export const EDITABLE_MEDIA_CLASS = "o_editable_media";

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
            (node.classList.contains("o_image") ||
                node.classList.contains("media_iframe_video"))) ||
        node.nodeName === "CANVAS"
    );
}

// See https://developer.mozilla.org/en-US/docs/Web/HTML/Content_categories#phrasing_content
const phrasingTagNames = new Set([
    "ABBR",
    "AUDIO",
    "B",
    "BDI",
    "BDO",
    "BR",
    "BUTTON",
    "CANVAS",
    "CITE",
    "CODE",
    "DATA",
    "DATALIST",
    "DFN",
    "EM",
    "EMBED",
    "I",
    "IFRAME",
    "IMG",
    "INPUT",
    "KBD",
    "LABEL",
    "MARK",
    "MATH",
    "METER",
    "NOSCRIPT",
    "OBJECT",
    "OUTPUT",
    "PICTURE",
    "PROGRESS",
    "Q",
    "RUBY",
    "S",
    "SAMP",
    "SCRIPT",
    "SELECT",
    "SLOT",
    "SMALL",
    "SPAN",
    "STRONG",
    "SUB",
    "SUP",
    "SVG",
    "TEMPLATE",
    "TEXTAREA",
    "TIME",
    "U",
    "VAR",
    "VIDEO",
    "WBR",
    "FONT", // TODO @phoenix: font is deprecated, replace usage
    // The following elements are phrasing content under specific conditions,
    // evaluate if those conditions are applicable when using this set.
    "A",
    "AREA",
    "DEL",
    "INS",
    "LINK",
    "MAP",
    "META",
]);

export function isPhrasingContent(node) {
    if (
        node &&
        (node.nodeType === Node.TEXT_NODE ||
            (node.nodeType === Node.ELEMENT_NODE && phrasingTagNames.has(node.tagName)))
    ) {
        return true;
    }
    return false;
}

export function containsAnyInline(element) {
    if (!element) {
        return false;
    }
    let child = element.firstChild;
    while (child) {
        if (
            (!isBlock(child) && child.nodeType === Node.ELEMENT_NODE) ||
            (child.nodeType === Node.TEXT_NODE && child.textContent.trim() !== "")
        ) {
            return true;
        }
        child = child.nextSibling;
    }
    return false;
}

export function containsAnyNonPhrasingContent(element) {
    if (!element) {
        return false;
    }
    let child = element.firstChild;
    while (child) {
        if (!isPhrasingContent(child)) {
            return true;
        }
        child = child.nextSibling;
    }
    return false;
}

export function isEmbeddedComponent(node) {
    return node.nodeType === Node.ELEMENT_NODE && node.matches("[data-embedded]");
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
    if (!node) {
        return false;
    }
    const candidate = node.parentElement
        ? closestElement(node.parentElement, "[data-oe-protected]")
        : null;
    if (!candidate || candidate.dataset.oeProtected === "false") {
        return false;
    }
    return true;
}

/**
 * A "protecting" element contains childNodes that are protected.
 *
 * @param {Node} node
 * @returns {boolean}
 */
export function isProtecting(node) {
    if (!node) {
        return false;
    }
    return (
        node.nodeType === Node.ELEMENT_NODE &&
        node.dataset.oeProtected !== "false" &&
        node.dataset.oeProtected !== undefined
    );
}

export function isUnprotecting(node) {
    if (!node) {
        return false;
    }
    return node.nodeType === Node.ELEMENT_NODE && node.dataset.oeProtected === "false";
}

// This is a list of "paragraph-related elements", defined as elements that
// behave like paragraphs. It is non-exhaustive and should not be used as a
// standalone. @see isParagraphRelatedElement
export const paragraphRelatedElements = ["P", "H1", "H2", "H3", "H4", "H5", "H6", "PRE"];

/**
 * Return true if the given node allows "paragraph-related elements".
 *
 * @see paragraphRelatedElements
 * @param {Node} node
 * @returns {boolean}
 */
export function allowsParagraphRelatedElements(node) {
    return isBlock(node) && !isParagraphRelatedElement(node);
}

export const phrasingContent = new Set(["#text", ...phrasingTagNames]);
const flowContent = new Set([...phrasingContent, ...paragraphRelatedElements, "DIV", "HR"]);
export const listItem = new Set(["LI"]);
const listContainers = new Set(["UL", "OL"]);

const allowedContent = {
    BLOCKQUOTE: flowContent,
    DIV: flowContent,
    H1: phrasingContent,
    H2: phrasingContent,
    H3: phrasingContent,
    H4: phrasingContent,
    H5: phrasingContent,
    H6: phrasingContent,
    HR: new Set(),
    LI: flowContent,
    OL: listItem,
    UL: listItem,
    P: phrasingContent,
    PRE: phrasingContent,
    TD: flowContent,
    TR: new Set(["TD"]),
};

export function isParagraphRelatedElement(node) {
    if (!node) {
        return false;
    }
    return (
        paragraphRelatedElements.includes(node.nodeName) ||
        (node.nodeType === Node.ELEMENT_NODE && node.matches(baseContainerGlobalSelector))
    );
}

export const paragraphRelatedElementsSelector = [
    ...paragraphRelatedElements,
    baseContainerGlobalSelector,
].join(",");

export function isListItemElement(node) {
    return [...listItem].includes(node.nodeName);
}

export const listItemElementSelector = [...listItem].join(",");

export function isListElement(node) {
    return [...listContainers].includes(node.nodeName);
}

export const listElementSelector = [...listContainers].join(",");

export function isTableCell(node) {
    return ["TH", "TD"].includes(node.nodeName);
}

/**
 * @param {Element} parentBlock
 * @param {Node[]} nodes
 * @returns {boolean}
 */
export function isAllowedContent(parentBlock, nodes) {
    let allowedContentSet = allowedContent[parentBlock.nodeName];
    if (!allowedContentSet) {
        // Spec: a block not listed in allowedContent allows anything.
        // See "custom-block" in tests.
        return true;
    }
    if (parentBlock.matches(baseContainerGlobalSelector)) {
        // A baseContainer DIV can only have phrasingContent, as a P would.
        allowedContentSet = phrasingContent;
    }
    return nodes.every((node) => allowedContentSet.has(node.nodeName));
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
    if (isProtecting(blockEl) || isProtected(blockEl)) {
        // Protecting nodes should never be considered empty for editor
        // operations, as their content is a "black box". Their content should
        // be managed by a specialized plugin.
        return false;
    }
    const nodes = blockEl.querySelectorAll("*");
    for (const node of nodes) {
        // There is no text and no double BR, the only thing that could make
        // this visible is a "visible empty" node like an image.
        if (
            node.nodeName != "BR" &&
            (isSelfClosingElement(node) ||
                isMediaElement(node) ||
                isProtecting(node) ||
                isButton(node))
        ) {
            return false;
        }
    }
    return isBlock(blockEl);
}
/**
 * Checks whether or not the given block element has something to make it have
 * a visible height (except for padding / border).
 *
 * @param {HTMLElement} blockEl
 * @returns {boolean}
 */
export function isShrunkBlock(blockEl) {
    return isEmptyBlock(blockEl) && !blockEl.querySelector("br") && !isSelfClosingElement(blockEl);
}

export function isEditorTab(node) {
    return node && node.nodeName === "SPAN" && node.classList.contains("oe-tabs");
}

export function getDeepestPosition(node, offset) {
    let direction = DIRECTIONS.RIGHT;
    let next = node;
    while (next) {
        if (isTangible(next) || (isZWS(next) && isContentEditable(next))) {
            // Valid node: update position then try to go deeper.
            if (next !== node) {
                [node, offset] = [next, direction ? 0 : nodeSize(next)];
            }
            // First switch direction to left if offset is at the end.
            const childrenNodes = childNodes(node);
            direction = offset < childrenNodes.length;
            next = childrenNodes[direction ? offset : offset - 1];
        } else if (direction && next.nextSibling && closestBlock(node).contains(next.nextSibling)) {
            // Invalid node: skip to next sibling (without crossing blocks).
            next = next.nextSibling;
        } else {
            // Invalid node: skip to previous sibling (without crossing blocks).
            direction = DIRECTIONS.LEFT;
            next = closestBlock(node).contains(next.previousSibling) && next.previousSibling;
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
    for (const name of new Set([...node.getAttributeNames(), ...node2.getAttributeNames()])) {
        if (name === "style") {
            if (!hasSameStyleAttributes(node, node2)) {
                return false;
            }
        } else if (name === "class") {
            if (!hasSameClasses(node, node2)) {
                return false; // The nodes don't have the same classes.
            }
        } else if (node.getAttribute(name) !== node2.getAttribute(name)) {
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
    if (isBlock(node)) {
        return false;
    }
    const nodeStyle = getComputedStyle(node);
    const node2Style = getComputedStyle(node2);
    if (node.matches("code.o_inline_code")) {
        if (nodeStyle.padding === node2Style.padding && nodeStyle.margin === node2Style.margin) {
            return true;
        }
    }
    return (
        !+nodeStyle.padding.replace(NOT_A_NUMBER, "") &&
        !+node2Style.padding.replace(NOT_A_NUMBER, "") &&
        !+nodeStyle.margin.replace(NOT_A_NUMBER, "") &&
        !+node2Style.margin.replace(NOT_A_NUMBER, "")
    );
}

export function hasSameStyleAttributes(node, node2) {
    const getNodeStyles = (node) =>
        (node.getAttribute("style") || "")
            .split(";")
            .map((style) => style.trim())
            .filter(Boolean);
    const [nodeStyles, node2Styles] = [node, node2].map(getNodeStyles);
    return (
        nodeStyles.length === node2Styles.length &&
        nodeStyles.every((style) => node2Styles.includes(style))
    );
}

export function hasSameClasses(node, node2) {
    const getNodeClasses = (node) =>
        (node.getAttribute("class") || "")
            .split(/\s+/)
            .map((c) => c.trim())
            .filter(Boolean);
    const [nodeClasses, node2Classes] = [node, node2].map(getNodeClasses);
    return (
        nodeClasses.length === node2Classes.length &&
        nodeClasses.every((cls) => node2Classes.includes(cls))
    );
}

export function isTextNode(node) {
    return node.nodeType === Node.TEXT_NODE;
}

export function isElement(node) {
    return node.nodeType === Node.ELEMENT_NODE;
}

export function isContentEditable(node) {
    const element = isTextNode(node) ? node.parentElement : node;
    return element && element.isContentEditable;
}

export function isContentEditableAncestor(node) {
    if (node.nodeType !== Node.ELEMENT_NODE) {
        return false;
    }
    return node.isContentEditable && node.matches("[contenteditable]");
}

/**
 * Checks if all classes in node are present in node2 (subset check)
 */
function hasClassesSubset(node, node2) {
    const getNodeClasses = (n) => (n || "").trim().split(/\s+/).filter(Boolean);
    const [nodeClasses, node2Classes] = [node, node2].map(getNodeClasses);
    return nodeClasses.every((cls) => node2Classes.includes(cls));
}

/**
 * Checks if all styles in node are present in node2 (subset check)
 */
function hasStylesSubset(node, node2) {
    const getNodeStyles = (n) =>
        (n || "")
            .split(";")
            .map((s) => s.trim())
            .filter(Boolean);
    const [nodeStyles, node2Styles] = [node, node2].map(getNodeStyles);
    return nodeStyles.every((style) => node2Styles.includes(style));
}

/**
 * Checks if a node is redundant based on its closest element with same tag.
 *
 * A node is considered redundant if:
 * - It is an Element node with a parent.
 * - There is a closest element with the same tag name.
 * - All of the node's attributes are present in that closest element:
 *   - All classes exist in the closest element's class list (subset check).
 *   - All inline styles are present in the closest element's style attribute (subset check).
 *   - All other attributes must have identical values.
 *
 * @param {Node} node - The DOM node to evaluate.
 * @returns {boolean} True if the node is redundant, false otherwise.
 */
export function isRedundantElement(node) {
    // Check for valid element node and existence of a parent.
    if (!node || node.nodeType !== Node.ELEMENT_NODE || !node.parentElement) {
        return false;
    }

    // Find the closest element with the same tag name.
    const closestEl = closestElement(node.parentElement, node.tagName);
    if (!closestEl) {
        return false;
    }

    // Check each attribute from node.
    for (const { name: attrName, value: nodeAttrVal } of node.attributes) {
        const closestElAttrVal = closestEl.getAttribute(attrName);

        if (!closestElAttrVal) {
            return false; // Attribute missing in closest element.
        }

        if (attrName === "class") {
            // All classes on the node must exist in closest element.
            if (!hasClassesSubset(nodeAttrVal, closestElAttrVal)) {
                return false;
            }
        } else if (attrName === "style") {
            // All inline styles on the node must exist in closest element.
            if (!hasStylesSubset(nodeAttrVal, closestElAttrVal)) {
                return false;
            }
        } else {
            // For other attributes, values must match exactly.
            if (nodeAttrVal !== closestElAttrVal) {
                return false;
            }
        }
    }

    return true;
}
