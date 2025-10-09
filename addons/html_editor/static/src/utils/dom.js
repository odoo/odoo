import { closestBlock, isBlock } from "./blocks";
import { isParagraphRelatedElement, isShrunkBlock, isVisible } from "./dom_info";
import { callbacksForCursorUpdate } from "./selection";
import { isEmptyBlock, isPhrasingContent } from "../utils/dom_info";
import { childNodes } from "./dom_traversal";
import { childNodeIndex, DIRECTIONS } from "./position";
import {
    baseContainerGlobalSelector,
    createBaseContainer,
} from "@html_editor/utils/base_container";

/** @typedef {import("@html_editor/core/selection_plugin").Cursors} Cursors */

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
            if (childIndex && isParagraphRelatedElement(child)) {
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

/**
 * Wrap inline children nodes in Blocks, optionally updating cursors for
 * later selection restore. A paragraph is used for phrasing node, and a div
 * is used otherwise.
 *
 * @param {HTMLElement} element - block element
 * @param {Cursors} [cursors]
 */
export function wrapInlinesInBlocks(
    element,
    { baseContainerNodeName = "P", cursors = { update: () => {} } } = {}
) {
    // Helpers to manipulate preserving selection.
    const wrapInBlock = (node, cursors) => {
        const block = isPhrasingContent(node)
            ? createBaseContainer(baseContainerNodeName, node.ownerDocument)
            : node.ownerDocument.createElement("DIV");
        cursors.update(callbacksForCursorUpdate.append(block, node));
        cursors.update(callbacksForCursorUpdate.before(node, block));
        if (node.nextSibling) {
            const sibling = node.nextSibling;
            node.remove();
            sibling.before(block);
        } else {
            const parent = node.parentElement;
            node.remove();
            parent.append(block);
        }
        block.append(node);
        return block;
    };
    const appendToCurrentBlock = (currentBlock, node, cursors) => {
        if (currentBlock.matches(baseContainerGlobalSelector) && !isPhrasingContent(node)) {
            const block = currentBlock.ownerDocument.createElement("DIV");
            cursors.update(callbacksForCursorUpdate.before(currentBlock, block));
            currentBlock.before(block);
            for (const child of childNodes(currentBlock)) {
                cursors.update(callbacksForCursorUpdate.append(block, child));
                block.append(child);
            }
            cursors.update(callbacksForCursorUpdate.remove(currentBlock));
            currentBlock.remove();
            currentBlock = block;
        }
        cursors.update(callbacksForCursorUpdate.append(currentBlock, node));
        currentBlock.append(node);
        return currentBlock;
    };
    const removeNode = (node, cursors) => {
        cursors.update(callbacksForCursorUpdate.remove(node));
        node.remove();
    };

    const children = childNodes(element);
    const visibleNodes = new Set(children.filter(isVisible));

    let currentBlock;
    let shouldBreakLine = true;
    for (const node of children) {
        if (isBlock(node)) {
            shouldBreakLine = true;
        } else if (!visibleNodes.has(node)) {
            removeNode(node, cursors);
        } else if (node.nodeName === "BR") {
            if (shouldBreakLine) {
                wrapInBlock(node, cursors);
            } else {
                // BR preceded by inline content: discard it and make sure
                // next inline goes in a new Block
                removeNode(node, cursors);
                shouldBreakLine = true;
            }
        } else if (shouldBreakLine) {
            currentBlock = wrapInBlock(node, cursors);
            shouldBreakLine = false;
        } else {
            currentBlock = appendToCurrentBlock(currentBlock, node, cursors);
        }
    }
}

export function unwrapContents(node) {
    const contents = childNodes(node);
    for (const child of contents) {
        node.parentNode.insertBefore(child, node);
    }
    node.parentNode.removeChild(node);
    return contents;
}

/**
 * Removes the specified class names from the given element.  If the element has
 * no more class names after removal, the "class" attribute is removed.
 *
 * @param {Element} element - The element from which to remove the class names.
 * @param {...string} classNames - The class names to be removed.
 */
export function removeClass(element, ...classNames) {
    const classNamesSet = new Set(classNames);
    if ([...element.classList].every((className) => classNamesSet.has(className))) {
        element.removeAttribute("class");
    } else {
        element.classList.remove(...classNames);
    }
}

export function removeStyle(element, ...styleProperties) {
    const propsToRemoveSet = new Set(styleProperties);
    if ([...element.style].every((prop) => propsToRemoveSet.has(prop))) {
        element.removeAttribute("style");
    } else {
        styleProperties.forEach((prop) => element.style.removeProperty(prop));
    }
}

/**
 * Add a BR in the given node if its closest ancestor block has nothing to make
 * it visible, and/or add a zero-width space in the given node if it's an empty
 * inline so the cursor can stay in it.
 *
 * @param {HTMLElement} el
 * @returns {Object} { br: the inserted <br> if any,
 *                     zws: the inserted zero-width space if any }
 */
export function fillEmpty(el) {
    const document = el.ownerDocument;
    if (!isBlock(el) && !isVisible(el) && !el.hasAttribute("data-oe-zws-empty-inline")) {
        const zws = document.createTextNode("\u200B");
        el.appendChild(zws);
        el.setAttribute("data-oe-zws-empty-inline", "");
        const previousSibling = el.previousSibling;
        if (previousSibling && previousSibling.nodeName === "BR") {
            previousSibling.remove();
        }
        return { zws };
    } else {
        // If a ZWS was inserted, there is no need for a <br>.
        return fillShrunkPhrasingParent(el);
    }
}

/**
 * Add a BR in a shrunk phrasing parent to make it visible.
 * A shrunk block is assumed to be a phrasing parent, and the inserted
 * <br> must be wrapped in a paragraph by the caller if necessary.
 *
 * @param {HTMLElement} el
 * @returns {Object} { br: the inserted <br> if any }
 */
export function fillShrunkPhrasingParent(el) {
    const document = el.ownerDocument;
    const fillers = {};
    const blockEl = closestBlock(el);
    if (isShrunkBlock(blockEl)) {
        const br = document.createElement("br");
        blockEl.appendChild(br);
        fillers.br = br;
    }
    return fillers;
}

/**
 * Removes a trailing BR if it is unnecessary:
 * in a non-empty block, if the last childNode is a BR and its previous sibling
 * is not a BR, remove the BR.
 *
 * @param {HTMLElement} el
 * @param {Array} predicates exceptions where a trailing BR should not be removed
 * @returns {HTMLElement|undefined} the removed br, if any
 */
export function cleanTrailingBR(el, predicates = []) {
    const candidate = el?.lastChild;
    if (
        candidate?.nodeName === "BR" &&
        candidate.previousSibling?.nodeName !== "BR" &&
        !isEmptyBlock(el) &&
        !predicates.some((predicate) => predicate(candidate))
    ) {
        candidate.remove();
        return candidate;
    }
}

/**
 * Wrapper for classList.toggle that removes the class attribute if the
 * element has no class name after the toggle.
 *
 * @param {Element} element
 * @param {string} className
 * @param {boolean} [force]
 */
export function toggleClass(element, className, force) {
    element.classList.toggle(className, force);
    if (!element.className) {
        element.removeAttribute("class");
    }
}

/**
 * Remove all occurrences of a character from a text node and optionally update
 * cursors for later selection restore.
 *
 * In web_editor the text nodes used to be replaced by new ones with the updated
 * text rather than just changing the text content of the node because it
 * creates different mutations and it used to break the tour system. In
 * html_editor the text content is changed instead because other plugins rely on
 * the reference to the text node.
 *
 * @param {Node} node text node
 * @param {String} char character to remove (string of length 1)
 * @param {Cursors} [cursors]
 */
export function cleanTextNode(node, char, cursors) {
    const removedIndexes = [];
    node.textContent = node.textContent.replaceAll(char, (_, offset) => {
        removedIndexes.push(offset);
        return "";
    });
    cursors?.update((cursor) => {
        if (cursor.node === node) {
            cursor.offset -= removedIndexes.filter((index) => cursor.offset > index).length;
        }
    });
}

/**
 * Splits a text node in two parts.
 * If the split occurs at the beginning or the end, the text node stays
 * untouched and unsplit. If a split actually occurs, the original text node
 * still exists and become the right part of the split.
 *
 * Note: if split after or before whitespace, that whitespace may become
 * invisible, it is up to the caller to replace it by nbsp if needed.
 *
 * @param {Text} textNode
 * @param {number} offset
 * @param {boolean} originalNodeSide Whether the original node ends up on left
 * or right after the split
 * @returns {number} The parentOffset if the cursor was between the two text
 *          node parts after the split.
 */
export function splitTextNode(textNode, offset, originalNodeSide = DIRECTIONS.RIGHT) {
    const document = textNode.ownerDocument;
    let parentOffset = childNodeIndex(textNode);

    if (offset > 0) {
        parentOffset++;

        if (offset < textNode.length) {
            const left = textNode.nodeValue.substring(0, offset);
            const right = textNode.nodeValue.substring(offset);
            if (originalNodeSide === DIRECTIONS.LEFT) {
                const newTextNode = document.createTextNode(right);
                textNode.after(newTextNode);
                textNode.nodeValue = left;
            } else {
                const newTextNode = document.createTextNode(left);
                textNode.before(newTextNode);
                textNode.nodeValue = right;
            }
        }
    }
    return parentOffset;
}
