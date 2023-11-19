import { closestBlock, isBlock } from "./blocks";
import {
    isSelfClosingElement,
    isShrunkBlock,
    isVisible,
    paragraphRelatedElements,
} from "./dom_info";
import { prepareUpdate } from "./dom_state";
import { boundariesOut, leftPos, nodeSize, rightPos } from "./position";

/**
 * Take a node and unwrap all of its block contents recursively. All blocks
 * (except for firstChilds) are preceded by a <br> in order to preserve the line
 * breaks.
 *
 * @param {Node} node
 */
export function makeContentsInline(node) {
    const document = node.ownerDocument;
    let childIndex = 0;
    for (const child of node.childNodes) {
        if (isBlock(child)) {
            if (childIndex && paragraphRelatedElements.includes(child.nodeName)) {
                child.before(document.createElement("br"));
            }
            for (const grandChild of child.childNodes) {
                child.before(grandChild);
                makeContentsInline(grandChild);
            }
            child.remove();
        }
        childIndex += 1;
    }
}

export function unwrapContents(node) {
    const contents = [...node.childNodes];
    for (const child of contents) {
        node.parentNode.insertBefore(child, node);
    }
    node.parentNode.removeChild(node);
    return contents;
}

// @todo @phoenix
// This utils seem to handle a particular case of LI element.
// If only relevant to the list plugin, a specific util should be created
// that plugin instead.
export function setTagName(el, newTagName) {
    const document = el.ownerDocument;
    if (el.tagName === newTagName) {
        return el;
    }
    const newEl = document.createElement(newTagName);
    while (el.firstChild) {
        newEl.append(el.firstChild);
    }
    if (el.tagName === "LI") {
        el.append(newEl);
    } else {
        for (const attribute of el.attributes) {
            newEl.setAttribute(attribute.name, attribute.value);
        }
        el.parentNode.replaceChild(newEl, el);
    }
    return newEl;
}

/**
 * Removes the specified class names from the given element.  If the element has
 * no more class names after removal, the "class" attribute is removed.
 *
 * @param {Element} element - The element from which to remove the class names.
 * @param {...string} classNames - The class names to be removed.
 */
export function removeClass(element, ...classNames) {
    element.classList.remove(...classNames);
    if (!element.classList.length) {
        element.removeAttribute("class");
    }
}

/**
 * Add a BR in the given node if its closest ancestor block has nothing to make
 * it visible, and/or add a zero-width space in the given node if it's an empty
 * inline unremovable so the cursor can stay in it.
 *
 * @param {HTMLElement} el
 * @returns {Object} { br: the inserted <br> if any,
 *                     zws: the inserted zero-width space if any }
 */
export function fillEmpty(el) {
    const document = el.ownerDocument;
    const fillers = {};
    const blockEl = closestBlock(el);
    if (isShrunkBlock(blockEl)) {
        const br = document.createElement("br");
        blockEl.appendChild(br);
        fillers.br = br;
    }
    if (!isVisible(el) && !el.hasAttribute("data-oe-zws-empty-inline")) {
        // As soon as there is actual content in the node, the zero-width space
        // is removed by the sanitize function.
        const zws = document.createTextNode("\u200B");
        el.appendChild(zws);
        el.setAttribute("data-oe-zws-empty-inline", "");
        fillers.zws = zws;
        const previousSibling = el.previousSibling;
        if (previousSibling && previousSibling.nodeName === "BR") {
            previousSibling.remove();
        }
    }
    return fillers;
}
/**
 * Moves the given subset of nodes of a source element to the given destination.
 * If the source element is left empty it is removed. This ensures the moved
 * content and its destination surroundings are restored (@see restoreState) to
 * the way there were.
 *
 * It also reposition at the right position on the left of the moved nodes.
 *
 * @param {HTMLElement} destinationEl
 * @param {number} destinationOffset
 * @param {HTMLElement} sourceEl
 * @param {number} [startIndex=0]
 * @param {number} [endIndex=sourceEl.childNodes.length]
 * @returns {Array.<HTMLElement, number} The position at the left of the moved
 *     nodes after the move was done (and where the cursor was returned).
 */
export function moveNodes(
    destinationEl,
    destinationOffset,
    sourceEl,
    startIndex = 0,
    endIndex = sourceEl.childNodes.length
) {
    if (isSelfClosingElement(destinationEl)) {
        throw new Error(`moveNodes: Invalid destination element ${destinationEl.nodeName}`);
    }

    const nodes = [];
    for (let i = startIndex; i < endIndex; i++) {
        nodes.push(sourceEl.childNodes[i]);
    }

    if (nodes.length) {
        const restoreDestination = prepareUpdate(destinationEl, destinationOffset);
        const restoreMoved = prepareUpdate(
            ...leftPos(sourceEl.childNodes[startIndex]),
            ...rightPos(sourceEl.childNodes[endIndex - 1])
        );
        const fragment = document.createDocumentFragment();
        nodes.forEach((node) => fragment.appendChild(node));
        const posRightNode = destinationEl.childNodes[destinationOffset];
        if (posRightNode) {
            destinationEl.insertBefore(fragment, posRightNode);
        } else {
            destinationEl.appendChild(fragment);
        }
        restoreDestination();
        restoreMoved();
    }

    if (!nodeSize(sourceEl)) {
        const restoreOrigin = prepareUpdate(...boundariesOut(sourceEl));
        sourceEl.remove();
        restoreOrigin();
    }

    // Return cursor position, but don't change it
    const firstNode = nodes.find((node) => !!node.parentNode);
    return firstNode ? leftPos(firstNode) : [destinationEl, destinationOffset];
}

export function toggleClass(node, className) {
    node.classList.toggle(className);
    if (!node.className) {
        node.removeAttribute("class");
    }
}
