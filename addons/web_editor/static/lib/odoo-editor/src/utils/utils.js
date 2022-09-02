/** @odoo-module **/

export const DIRECTIONS = {
    LEFT: false,
    RIGHT: true,
};
export const CTYPES = {
    // Short for CONTENT_TYPES
    // Inline group
    CONTENT: 1,
    SPACE: 2,

    // Block group
    BLOCK_OUTSIDE: 4,
    BLOCK_INSIDE: 8,

    // Br group
    BR: 16,
};
export const CTGROUPS = {
    // Short for CONTENT_TYPE_GROUPS
    INLINE: CTYPES.CONTENT | CTYPES.SPACE,
    BLOCK: CTYPES.BLOCK_OUTSIDE | CTYPES.BLOCK_INSIDE,
    BR: CTYPES.BR,
};
const tldWhitelist = [
    'com', 'net', 'org', 'ac', 'ad', 'ae', 'af', 'ag', 'ai', 'al', 'am', 'an',
    'ao', 'aq', 'ar', 'as', 'at', 'au', 'aw', 'ax', 'az', 'ba', 'bb', 'bd',
    'be', 'bf', 'bg', 'bh', 'bi', 'bj', 'bl', 'bm', 'bn', 'bo', 'br', 'bq',
    'bs', 'bt', 'bv', 'bw', 'by', 'bz', 'ca', 'cc', 'cd', 'cf', 'cg', 'ch',
    'ci', 'ck', 'cl', 'cm', 'cn', 'co', 'cr', 'cs', 'cu', 'cv', 'cw', 'cx',
    'cy', 'cz', 'dd', 'de', 'dj', 'dk', 'dm', 'do', 'dz', 'ec', 'ee', 'eg',
    'eh', 'er', 'es', 'et', 'eu', 'fi', 'fj', 'fk', 'fm', 'fo', 'fr', 'ga',
    'gb', 'gd', 'ge', 'gf', 'gg', 'gh', 'gi', 'gl', 'gm', 'gn', 'gp', 'gq',
    'gr', 'gs', 'gt', 'gu', 'gw', 'gy', 'hk', 'hm', 'hn', 'hr', 'ht', 'hu',
    'id', 'ie', 'il', 'im', 'in', 'io', 'iq', 'ir', 'is', 'it', 'je', 'jm',
    'jo', 'jp', 'ke', 'kg', 'kh', 'ki', 'km', 'kn', 'kp', 'kr', 'kw', 'ky',
    'kz', 'la', 'lb', 'lc', 'li', 'lk', 'lr', 'ls', 'lt', 'lu', 'lv', 'ly',
    'ma', 'mc', 'md', 'me', 'mf', 'mg', 'mh', 'mk', 'ml', 'mm', 'mn', 'mo',
    'mp', 'mq', 'mr', 'ms', 'mt', 'mu', 'mv', 'mw', 'mx', 'my', 'mz', 'na',
    'nc', 'ne', 'nf', 'ng', 'ni', 'nl', 'no', 'np', 'nr', 'nu', 'nz', 'om',
    'pa', 'pe', 'pf', 'pg', 'ph', 'pk', 'pl', 'pm', 'pn', 'pr', 'ps', 'pt',
    'pw', 'py', 'qa', 're', 'ro', 'rs', 'ru', 'rw', 'sa', 'sb', 'sc', 'sd',
    'se', 'sg', 'sh', 'si', 'sj', 'sk', 'sl', 'sm', 'sn', 'so', 'sr', 'ss',
    'st', 'su', 'sv', 'sx', 'sy', 'sz', 'tc', 'td', 'tf', 'tg', 'th', 'tj',
    'tk', 'tl', 'tm', 'tn', 'to', 'tp', 'tr', 'tt', 'tv', 'tw', 'tz', 'ua',
    'ug', 'uk', 'um', 'us', 'uy', 'uz', 'va', 'vc', 've', 'vg', 'vi', 'vn',
    'vu', 'wf', 'ws', 'ye', 'yt', 'yu', 'za', 'zm', 'zr', 'zw', 'co\\.uk'];

const urlRegexBase = `|(?:[-a-zA-Z0-9@:%._\\+~#=]{1,64}\\.))[-a-zA-Z0-9@:%._\\+~#=]{2,256}\\.[a-zA-Z][a-zA-Z0-9]{1,62}|(?:[-a-zA-Z0-9@:%._\\+~#=]{2,256}\\.(?:${tldWhitelist.join('|')})))\\b(?:(?!\\.)[^\\s]*`;
const httpRegex = `(?:https?:\\/\\/)`;
const httpCapturedRegex= `(https?:\\/\\/)`;

export const URL_REGEX = new RegExp(`((?:(?:${httpRegex}${urlRegexBase}))`, 'gi');
export const URL_REGEX_WITH_INFOS = new RegExp(`((?:(?:${httpCapturedRegex}${urlRegexBase}))`, 'gi');
export const YOUTUBE_URL_GET_VIDEO_ID =
    /^(?:(?:https?:)?\/\/)?(?:(?:www|m)\.)?(?:youtube\.com|youtu\.be)(?:\/(?:[\w-]+\?v=|embed\/|v\/)?)([^\s?&#]+)(?:\S+)?$/i;

//------------------------------------------------------------------------------
// Position and sizes
//------------------------------------------------------------------------------

/**
 * @param {Node} node
 * @returns {Array.<HTMLElement, number>}
 */
export function leftPos(node) {
    return [node.parentNode, childNodeIndex(node)];
}
/**
 * @param {Node} node
 * @returns {Array.<HTMLElement, number>}
 */
export function rightPos(node) {
    return [node.parentNode, childNodeIndex(node) + 1];
}
/**
 * @param {Node} node
 * @returns {Array.<HTMLElement, number, HTMLElement, number>}
 */
export function boundariesOut(node) {
    const index = childNodeIndex(node);
    return [node.parentNode, index, node.parentNode, index + 1];
}
/**
 * @param {Node} node
 * @returns {Array.<Node, number>}
 */
export function startPos(node) {
    return [node, 0];
}
/**
 * @param {Node} node
 * @returns {Array.<Node, number>}
 */
export function endPos(node) {
    return [node, nodeSize(node)];
}
/**
 * @param {Node} node
 * @returns {Array.<node, number, node, number>}
 */
export function boundariesIn(node) {
    return [node, 0, node, nodeSize(node)];
}
/**
 * Returns the given node's position relative to its parent (= its index in the
 * child nodes of its parent).
 *
 * @param {Node} node
 * @returns {number}
 */
export function childNodeIndex(node) {
    let i = 0;
    while (node.previousSibling) {
        i++;
        node = node.previousSibling;
    }
    return i;
}
/**
 * Returns the size of the node = the number of characters for text nodes and
 * the number of child nodes for element nodes.
 *
 * @param {Node} node
 * @returns {number}
 */
export function nodeSize(node) {
    const isTextNode = node.nodeType === Node.TEXT_NODE;
    return isTextNode ? node.length : node.childNodes.length;
}

//------------------------------------------------------------------------------
// DOM Path and node search functions
//------------------------------------------------------------------------------

export const closestPath = function* (node) {
    while (node) {
        yield node;
        node = node.parentNode;
    }
};

/**
 * Values which can be returned while browsing the DOM which gives information
 * to why the path ended.
 */
const PATH_END_REASONS = {
    NO_NODE: 0,
    BLOCK_OUT: 1,
    BLOCK_HIT: 2,
    OUT_OF_SCOPE: 3,
};
/**
 * Creates a generator function according to the given parameters. Pre-made
 * generators to traverse the DOM are made using this function:
 *
 * @see leftLeafFirstPath
 * @see leftLeafOnlyNotBlockPath
 * @see leftLeafOnlyInScopeNotBlockNoEditablePath
 * @see rightLeafOnlyNotBlockPath
 * @see rightLeafOnlyPathNotBlockNotEditablePath
 * @see rightLeafOnlyInScopeNotBlockPath
 * @see rightLeafOnlyNotBlockNotEditablePath
 *
 * @param {number} direction
 * @param {boolean} [options.leafOnly] if true, do not yield any non-leaf node
 * @param {boolean} [options.inScope] if true, stop the generator as soon as a node is not
 *                      a descendant of `node` provided when traversing the
 *                      generated function.
 * @param {Function} [options.stopTraverseFunction] a function that takes a node
 *                      and should return true when a node descendant should not
 *                      be traversed.
 * @param {Function} [options.stopFunction] function that makes the generator stop when a
 *                      node is encountered.
 */
export function createDOMPathGenerator(
    direction,
    { leafOnly = false, inScope = false, stopTraverseFunction, stopFunction } = {},
) {
    const nextDeepest =
        direction === DIRECTIONS.LEFT
            ? node => lastLeaf(node.previousSibling, stopTraverseFunction)
            : node => firstLeaf(node.nextSibling, stopTraverseFunction);

    const firstNode =
        direction === DIRECTIONS.LEFT
            ? (node, offset) => lastLeaf(node.childNodes[offset - 1], stopTraverseFunction)
            : (node, offset) => firstLeaf(node.childNodes[offset], stopTraverseFunction);

    // Note "reasons" is a way for the caller to be able to know why the
    // generator ended yielding values.
    return function* (node, offset, reasons = []) {
        let movedUp = false;

        let currentNode = firstNode(node, offset);
        if (!currentNode) {
            movedUp = true;
            currentNode = node;
        }

        while (currentNode) {
            if (stopFunction && stopFunction(currentNode)) {
                reasons.push(movedUp ? PATH_END_REASONS.BLOCK_OUT : PATH_END_REASONS.BLOCK_HIT);
                break;
            }
            if (inScope && currentNode === node) {
                reasons.push(PATH_END_REASONS.OUT_OF_SCOPE);
                break;
            }
            if (!(leafOnly && movedUp)) {
                yield currentNode;
            }

            movedUp = false;
            let nextNode = nextDeepest(currentNode);
            if (!nextNode) {
                movedUp = true;
                nextNode = currentNode.parentNode;
            }
            currentNode = nextNode;
        }

        reasons.push(PATH_END_REASONS.NO_NODE);
    };
}

/**
 * Find a node.
 * @param {findCallback} findCallback - This callback check if this function
 *      should return `node`.
 * @param {findCallback} stopCallback - This callback check if this function
 *      should stop when it receive `node`.
 */
export function findNode(domPath, findCallback = () => true, stopCallback = () => false) {
    for (const node of domPath) {
        if (findCallback(node)) {
            return node;
        }
        if (stopCallback(node)) {
            break;
        }
    }
    return null;
}
/**
 * This callback check if findNode should return `node`.
 * @callback findCallback
 * @param {Node} node
 * @return {Boolean}
 */
/**
 * This callback check if findNode should stop when it receive `node`.
 * @callback stopCallback
 * @param {Node} node
 */

/**
 * Returns the closest HTMLElement of the provided Node
 * if a 'selector' is provided, Returns the closest HTMLElement that match the selector
 *
 * @param {Node} node
 * @param {string} [selector=undefined]
 * @param {boolean} [restrictToEditable=false]
 * @returns {HTMLElement}
 */
export function closestElement(node, selector, restrictToEditable=false) {
    const element = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
    if (restrictToEditable && selector && element) {
        const elementFound = element.closest(selector);
        return elementFound && elementFound.querySelector('.odoo-editor-editable') ? null : elementFound;
    }
    return selector && element ? element.closest(selector) : element || node;
}

/**
 * Returns a list of all the ancestors nodes of the provided node.
 *
 * @param {Node} node
 * @param {Node} [editable] include to prevent bubbling up further than the editable.
 * @returns {HTMLElement[]}
 */
export function ancestors(node, editable) {
    if (!node || !node.parentElement || node === editable) return [];
    return [node.parentElement, ...ancestors(node.parentElement, editable)];
}

/**
 * Take a node, return all of its descendants, in depth-first order.
 *
 * @param {Node} node
 * @returns {Node[]}
 */
export function descendants(node) {
    const posterity = [];
    for (const child of (node.childNodes || [])) {
        posterity.push(child, ...descendants(child));
    }
    return posterity;
}

export function closestBlock(node) {
    return findNode(closestPath(node), node => isBlock(node));
}
/**
 * Returns the deepest child in last position.
 *
 * @param {Node} node
 * @param {Function} [stopTraverseFunction]
 * @returns {Node}
 */
export function lastLeaf(node, stopTraverseFunction) {
    while (node && node.lastChild && !(stopTraverseFunction && stopTraverseFunction(node))) {
        node = node.lastChild;
    }
    return node;
}
/**
 * Returns the deepest child in first position.
 *
 * @param {Node} node
 * @param {Function} [stopTraverseFunction]
 * @returns {Node}
 */
export function firstLeaf(node, stopTraverseFunction) {
    while (node && node.firstChild && !(stopTraverseFunction && stopTraverseFunction(node))) {
        node = node.firstChild;
    }
    return node;
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
/**
 * Returns all the previous siblings of the given node until the first
 * sibling that does not satisfy the predicate, in lookup order.
 *
 * @param {Node} node
 * @param {Function} [predicate] (node: Node) => boolean
 */
export function getAdjacentPreviousSiblings(node, predicate = n => !!n) {
    let previous = node.previousSibling;
    const list = [];
    while (previous && predicate(previous)) {
        list.push(previous);
        previous = previous.previousSibling;
    }
    return list;
}
/**
 * Returns all the next siblings of the given node until the first
 * sibling that does not satisfy the predicate, in lookup order.
 *
 * @param {Node} node
 * @param {Function} [predicate] (node: Node) => boolean
 */
export function getAdjacentNextSiblings(node, predicate = n => !!n) {
    let next = node.nextSibling;
    const list = [];
    while (next && predicate(next)) {
        list.push(next);
        next = next.nextSibling;
    }
    return list;
}
/**
 * Returns all the adjacent siblings of the given node until the first sibling
 * (in both directions) that does not satisfy the predicate, in index order. If
 * the given node does not satisfy the predicate, an empty array is returned.
 *
 * @param {Node} node
 * @param {Function} [predicate] (node: Node) => boolean
 */
export function getAdjacents(node, predicate = n => !!n) {
    const previous = getAdjacentPreviousSiblings(node, predicate);
    const next = getAdjacentNextSiblings(node, predicate);
    return predicate(node) ? [...previous.reverse(), node, ...next] : [];
}

//------------------------------------------------------------------------------
// Cursor management
//------------------------------------------------------------------------------

/**
 * From a given position, returns the normalized version.
 *
 * E.g. <b>abc</b>[]def -> <b>abc[]</b>def
 *
 * @param {Node} node
 * @param {number} offset
 * @param {boolean} [full=true] (if not full, it means we only normalize
 *     positions which are not possible, like the cursor inside an image).
 */
export function getNormalizedCursorPosition(node, offset, full = true) {
    if (isVisibleEmpty(node) || !closestElement(node).isContentEditable) {
        // Cannot put cursor inside those elements, put it after instead.
        [node, offset] = rightPos(node);
    }

    // Be permissive about the received offset.
    offset = Math.min(Math.max(offset, 0), nodeSize(node));

    if (full) {
        // Put the cursor in deepest inline node around the given position if
        // possible.
        let el;
        let elOffset;
        if (node.nodeType === Node.ELEMENT_NODE) {
            el = node;
            elOffset = offset;
        } else if (node.nodeType === Node.TEXT_NODE) {
            if (offset === 0) {
                el = node.parentNode;
                elOffset = childNodeIndex(node);
            } else if (offset === node.length) {
                el = node.parentNode;
                elOffset = childNodeIndex(node) + 1;
            }
        }
        if (el) {
            const leftInlineNode = leftLeafOnlyInScopeNotBlockNoEditablePath(el, elOffset).next()
                .value;
            let leftVisibleEmpty = false;
            if (leftInlineNode) {
                leftVisibleEmpty =
                    isVisibleEmpty(leftInlineNode) ||
                    !closestElement(leftInlineNode).isContentEditable;
                [node, offset] = leftVisibleEmpty
                    ? rightPos(leftInlineNode)
                    : endPos(leftInlineNode);
            }
            if (!leftInlineNode || leftVisibleEmpty) {
                const rightInlineNode = rightLeafOnlyInScopeNotBlockPath(el, elOffset).next().value;
                if (rightInlineNode) {
                    const rightVisibleEmpty =
                        isVisibleEmpty(rightInlineNode) ||
                        !closestElement(rightInlineNode).isContentEditable;
                    if (!(leftVisibleEmpty && rightVisibleEmpty)) {
                        [node, offset] = rightVisibleEmpty
                            ? leftPos(rightInlineNode)
                            : startPos(rightInlineNode);
                    }
                }
            }
        }
    }

    const prevNode = node.nodeType === Node.ELEMENT_NODE && node.childNodes[offset - 1];
    if (prevNode && prevNode.nodeName === 'BR' && isFakeLineBreak(prevNode)) {
        // If trying to put the cursor on the right of a fake line break, put
        // it before instead.
        offset--;
    }

    return [node, offset];
}
/**
 * @param {Node} anchorNode
 * @param {number} anchorOffset
 * @param {Node} focusNode
 * @param {number} focusOffset
 * @param {boolean} [normalize=true]
 * @returns {?Array.<Node, number}
 */
export function setSelection(
    anchorNode,
    anchorOffset,
    focusNode = anchorNode,
    focusOffset = anchorOffset,
    normalize = true,
) {
    if (
        !anchorNode ||
        !anchorNode.parentNode ||
        !anchorNode.parentNode.closest('body') ||
        !focusNode ||
        !focusNode.parentNode ||
        !focusNode.parentNode.closest('body')
    ) {
        return null;
    }
    const document = anchorNode.ownerDocument;

    const seemsCollapsed = anchorNode === focusNode && anchorOffset === focusOffset;
    [anchorNode, anchorOffset] = getNormalizedCursorPosition(anchorNode, anchorOffset, normalize);
    [focusNode, focusOffset] = seemsCollapsed
        ? [anchorNode, anchorOffset]
        : getNormalizedCursorPosition(focusNode, focusOffset, normalize);

    const direction = getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset);
    const sel = document.getSelection();
    if (!sel) {
        return null;
    }
    const range = new Range();
    if (direction === DIRECTIONS.RIGHT) {
        range.setStart(anchorNode, anchorOffset);
        range.collapse(true);
    } else {
        range.setEnd(anchorNode, anchorOffset);
        range.collapse(false);
    }
    sel.removeAllRanges();
    sel.addRange(range);
    sel.extend(focusNode, focusOffset);

    return [anchorNode, anchorOffset, focusNode, focusOffset];
}
/**
 * @param {Node} node
 * @param {boolean} [normalize=true]
 * @returns {?Array.<Node, number}
 */
export function setCursorStart(node, normalize = true) {
    const pos = startPos(node);
    return setSelection(...pos, ...pos, normalize);
}
/**
 * @param {Node} node
 * @param {boolean} [normalize=true]
 * @returns {?Array.<Node, number}
 */
export function setCursorEnd(node, normalize = true) {
    const pos = endPos(node);
    return setSelection(...pos, ...pos, normalize);
}
/**
 * From selection position, checks if it is left-to-right or right-to-left.
 *
 * @param {Node} anchorNode
 * @param {number} anchorOffset
 * @param {Node} focusNode
 * @param {number} focusOffset
 * @returns {boolean} the direction of the current range if the selection not is collapsed | false
 */
export function getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset) {
    if (anchorNode === focusNode) {
        if (anchorOffset === focusOffset) return false;
        return anchorOffset < focusOffset ? DIRECTIONS.RIGHT : DIRECTIONS.LEFT;
    }
    return anchorNode.compareDocumentPosition(focusNode) & Node.DOCUMENT_POSITION_FOLLOWING
        ? DIRECTIONS.RIGHT
        : DIRECTIONS.LEFT;
}
/**
 * Returns an array containing all the nodes traversed when walking the
 * selection.
 *
 * @param {Node} editable
 * @returns {Node[]}
 */
export function getTraversedNodes(editable, range = getDeepRange(editable)) {
    const document = editable.ownerDocument;
    if (!range) return [];
    const iterator = document.createNodeIterator(range.commonAncestorContainer);
    let node;
    do {
        node = iterator.nextNode();
    } while (node && node !== range.startContainer);
    const traversedNodes = [node];
    while (node && node !== range.endContainer) {
        node = iterator.nextNode();
        node && traversedNodes.push(node);
    }
    return traversedNodes;
}
/**
 * Returns an array containing all the nodes fully contained in the selection.
 *
 * @param {Node} editable
 * @returns {Node[]}
 */
export function getSelectedNodes(editable) {
    const document = editable.ownerDocument;
    const sel = document.getSelection();
    if (!sel.rangeCount) {
        return [];
    }
    const range = sel.getRangeAt(0);
    return getTraversedNodes(editable).filter(
        node => range.isPointInRange(node, 0) && range.isPointInRange(node, nodeSize(node)),
    );
}

/**
 * Returns the current range (if any), adapted to target the deepest
 * descendants.
 *
 * @param {Node} editable
 * @param {object} [options]
 * @param {Selection} [options.range] the range to use.
 * @param {Selection} [options.sel] the selection to use.
 * @param {boolean} [options.splitText] split the targeted text nodes at offset.
 * @param {boolean} [options.select] select the new range if it changed (via splitText).
 * @param {boolean} [options.correctTripleClick] adapt the range if it was a triple click.
 * @returns {Range}
 */
export function getDeepRange(editable, { range, sel, splitText, select, correctTripleClick } = {}) {
    sel = sel || editable.ownerDocument.getSelection();
    range = range ? range.cloneRange() : sel.rangeCount && sel.getRangeAt(0).cloneRange();
    if (!range) return;
    let start = range.startContainer;
    let startOffset = range.startOffset;
    let end = range.endContainer;
    let endOffset = range.endOffset;

    const isBackwards =
        !range.collapsed && start === sel.focusNode && startOffset === sel.focusOffset;

    // Target the deepest descendant of the range nodes.
    [start, startOffset] = getDeepestPosition(start, startOffset);
    [end, endOffset] = getDeepestPosition(end, endOffset);

    // Split text nodes if that was requested.
    if (splitText) {
        const isInSingleContainer = start === end;
        if (
            end.nodeType === Node.TEXT_NODE &&
            endOffset !== 0 &&
            endOffset !== end.textContent.length
        ) {
            const endParent = end.parentNode;
            const splitOffset = splitTextNode(end, endOffset);
            end = endParent.childNodes[splitOffset - 1] || endParent.firstChild;
            if (isInSingleContainer) {
                start = end;
            }
            endOffset = end.textContent.length;
        }
        if (
            start.nodeType === Node.TEXT_NODE &&
            startOffset !== 0 &&
            startOffset !== start.textContent.length
        ) {
            splitTextNode(start, startOffset);
            startOffset = 0;
            if (isInSingleContainer) {
                endOffset = start.textContent.length;
            }
        }
    }
    // A selection spanning multiple nodes and ending at position 0 of a
    // node, like the one resulting from a triple click, are corrected so
    // that it ends at the last position of the previous node instead.
    const beforeEnd = end.previousSibling;
    if (
        correctTripleClick &&
        !endOffset &&
        (start !== end || startOffset !== endOffset) &&
        (!beforeEnd || (beforeEnd.nodeType === Node.TEXT_NODE && !isVisibleStr(beforeEnd)))
    ) {
        const previous = previousLeaf(end, editable, true);
        if (previous && closestElement(previous).isContentEditable) {
            [end, endOffset] = [previous, nodeSize(previous)];
        }
    }

    if (select) {
        if (isBackwards) {
            [start, end, startOffset, endOffset] = [end, start, endOffset, startOffset];
            range.setEnd(start, startOffset);
            range.collapse(false);
        } else {
            range.setStart(start, startOffset);
            range.collapse(true);
        }
        sel.removeAllRanges();
        sel.addRange(range);
        try {
            sel.extend(end, endOffset);
        } catch (e) {
            // Firefox yells not happy when setting selection on elem with contentEditable=false.
        }
        range = sel.getRangeAt(0);
    } else {
        range.setStart(start, startOffset);
        range.setEnd(end, endOffset);
    }
    return range;
}

function getNextVisibleNode(node) {
    while (node && !isVisible(node)) {
        node = node.nextSibling;
    }
    return node;
}

export function getDeepestPosition(node, offset) {
    let found = false;
    while (node.hasChildNodes()) {
        let newNode = node.childNodes[offset];
        if (newNode) {
            newNode = getNextVisibleNode(newNode);
            if (!newNode || isVisibleEmpty(newNode)) break;
            found = true;
            node = newNode;
            offset = 0;
        } else {
            break;
        }
    }
    if (!found) {
        while (node.hasChildNodes()) {
            let newNode = node.childNodes[offset - 1];
            newNode = getNextVisibleNode(newNode);
            if (!newNode || isVisibleEmpty(newNode)) break;
            node = newNode;
            offset = nodeSize(node);
        }
    }
    let didMove = false;
    let reversed = false;
    while (!isVisible(node) && (node.previousSibling || (!reversed && node.nextSibling))) {
        reversed = reversed || !node.nextSibling;
        node = reversed ? node.previousSibling : node.nextSibling;
        offset = reversed ? nodeSize(node) : 0;
        didMove = true;
    }
    return didMove && isVisible(node) ? getDeepestPosition(node, offset) : [node, offset];
}

export function getCursors(document) {
    const sel = document.getSelection();
    if (
        getCursorDirection(sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset) ===
        DIRECTIONS.LEFT
    )
        return [
            [sel.focusNode, sel.focusOffset],
            [sel.anchorNode, sel.anchorOffset],
        ];
    return [
        [sel.anchorNode, sel.anchorOffset],
        [sel.focusNode, sel.focusOffset],
    ];
}

export function preserveCursor(document) {
    const sel = document.getSelection();
    const cursorPos = [sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset];
    return replace => {
        replace = replace || new Map();
        cursorPos[0] = replace.get(cursorPos[0]) || cursorPos[0];
        cursorPos[2] = replace.get(cursorPos[2]) || cursorPos[2];
        setSelection(...cursorPos);
    };
}

//------------------------------------------------------------------------------
// DOM Info utils
//------------------------------------------------------------------------------

/**
 * The following is a complete list of all HTML "block-level" elements.
 *
 * Source:
 * https://developer.mozilla.org/en-US/docs/Web/HTML/Block-level_elements
 *
 **/
const blockTagNames = [
    'ADDRESS',
    'ARTICLE',
    'ASIDE',
    'BLOCKQUOTE',
    'DETAILS',
    'DIALOG',
    'DD',
    'DIV',
    'DL',
    'DT',
    'FIELDSET',
    'FIGCAPTION',
    'FIGURE',
    'FOOTER',
    'FORM',
    'H1',
    'H2',
    'H3',
    'H4',
    'H5',
    'H6',
    'HEADER',
    'HGROUP',
    'HR',
    'LI',
    'MAIN',
    'NAV',
    'OL',
    'P',
    'PRE',
    'SECTION',
    'TABLE',
    'UL',
    // The following elements are not in the W3C list, for some reason.
    'SELECT',
    'OPTION',
    'TR',
    'TD',
    'TBODY',
    'THEAD',
    'TH',
];
const computedStyles = new WeakMap();
/**
 * Return true if the given node is a block-level element, false otherwise.
 *
 * @param node
 */
export function isBlock(node) {
    if (node.nodeType !== Node.ELEMENT_NODE) {
        return false;
    }
    const tagName = node.nodeName.toUpperCase();
    // Every custom jw-* node will be considered as blocks.
    if (
        tagName.startsWith('JW-') ||
        (tagName === 'T' &&
            node.getAttribute('t-esc') === null &&
            node.getAttribute('t-out') === null &&
            node.getAttribute('t-raw') === null)
    ) {
        return true;
    }
    if (tagName === 'BR') {
        // A <br> is always inline but getComputedStyle(br).display mistakenly
        // returns 'block' if its parent is display:flex (at least on Chrome and
        // Firefox (Linux)). Browsers normally support setting a <br>'s display
        // property to 'none' but any other change is not supported. Therefore
        // it is safe to simply declare that a <br> is never supposed to be a
        // block.
        return false;
    }
    // The node might not be in the DOM, in which case it has no CSS values.
    if (window.document !== node.ownerDocument) {
        return blockTagNames.includes(tagName);
    }
    // We won't call `getComputedStyle` more than once per node.
    let style = computedStyles.get(node);
    if (!style) {
        style = window.getComputedStyle(node);
        computedStyles.set(node, style);
    }
    if (style.display) {
        return !style.display.includes('inline') && style.display !== 'contents';
    }
    return blockTagNames.includes(tagName);
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
    return getComputedStyle(closestElement(node)).fontStyle === 'italic';
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
        if (getComputedStyle(parent).textDecorationLine === 'underline') {
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
        if (getComputedStyle(parent).textDecorationLine === 'line-through') {
            return true;
        }
        parent = parent.parentElement;
    }
    return false;
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
    const defaultDirection = editable.getAttribute('dir');
    return getComputedStyle(closestElement(node)).direction !== defaultDirection;
}
export const isFormat = {
    bold: isBold,
    italic: isItalic,
    underline: isUnderline,
    strikeThrough: isStrikeThrough,
    switchDirection: isDirectionSwitched,
};
/**
 * Return true if the current selection on the editable appears as the given
 * format. The selection is considered to appear as that format if every text
 * node in it appears as that format.
 *
 * @param {Element} editable
 * @param {String} format 'bold'|'italic'|'underline'|'strikeThrough'|'switchDirection'
 * @returns {boolean}
 */
export function isSelectionFormat(editable, format) {
    const selectedText = getSelectedNodes(editable)
        .filter(n => n.nodeType === Node.TEXT_NODE && n.nodeValue.trim().length);
    if (selectedText.length) {
        return selectedText.every(n => isFormat[format](n.parentElement, editable))
    } else {
        return isFormat[format](closestElement(editable.ownerDocument.getSelection().anchorNode), editable);
    }
}

export function isUnbreakable(node) {
    if (!node || node.nodeType === Node.TEXT_NODE) {
        return false;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) {
        return true;
    }
    return (
        isUnremovable(node) || // An unremovable node is always unbreakable.
        ['THEAD', 'TBODY', 'TFOOT', 'TR', 'TH', 'TD', 'SECTION', 'DIV'].includes(node.tagName) ||
        node.hasAttribute('t') ||
        (node.nodeType === Node.ELEMENT_NODE &&
            (node.nodeName === 'T' ||
                node.getAttribute('t-if') ||
                node.getAttribute('t-esc') ||
                node.getAttribute('t-elif') ||
                node.getAttribute('t-else') ||
                node.getAttribute('t-foreach') ||
                node.getAttribute('t-value') ||
                node.getAttribute('t-out') ||
                node.getAttribute('t-raw'))) ||
        node.classList.contains('oe_unbreakable')
    );
}

export function isUnremovable(node) {
    if (node.nodeType !== Node.ELEMENT_NODE && node.nodeType !== Node.TEXT_NODE) {
        return true;
    }
    return (
        node.oid === 'root' ||
        (node.nodeType === Node.ELEMENT_NODE &&
            (node.classList.contains('o_editable') || node.getAttribute('t-set') || node.getAttribute('t-call'))) ||
        (node.classList && node.classList.contains('oe_unremovable'))
    );
}

export function containsUnbreakable(node) {
    if (!node) {
        return false;
    }
    return isUnbreakable(node) || containsUnbreakable(node.firstChild);
}
export function isFontAwesome(node) {
    return (
        node &&
        (node.nodeName === 'I' || node.nodeName === 'SPAN') &&
        ['fa', 'fab', 'fad', 'far'].some(faClass => node.classList.contains(faClass))
    );
}
export function isZWS(node) {
    return (
        node &&
        node.textContent === '\u200B'
    );
}
export function isMediaElement(node) {
    return (
        isFontAwesome(node) ||
        (node.classList &&
            (node.classList.contains('o_image') || node.classList.contains('media_iframe_video')))
    );
}

export function containsUnremovable(node) {
    if (!node) {
        return false;
    }
    return isUnremovable(node) || containsUnremovable(node.firstChild);
}

export function getInSelection(document, selector) {
    const selection = document.getSelection();
    const range = selection && !!selection.rangeCount && selection.getRangeAt(0);
    return (
        range &&
        (closestElement(range.startContainer, selector) ||
            [...closestElement(range.commonAncestorContainer).querySelectorAll(selector)].find(
                node => range.intersectsNode(node),
            ))
    );
}

// This is a list of "paragraph-related elements", defined as elements that
// behave like paragraphs.
const paragraphRelatedElements = [
    'P',
    'H1',
    'H2',
    'H3',
    'H4',
    'H5',
    'H6',
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
 * Take a node and unwrap all of its block contents recursively. All blocks
 * (except for firstChilds) are preceded by a <br> in order to preserve the line
 * breaks.
 *
 * @param {Node} node
 */
export function makeContentsInline(node) {
    let childIndex = 0;
    for (const child of node.childNodes) {
        if (isBlock(child)) {
            if (childIndex && paragraphRelatedElements.includes(child.nodeName)) {
                child.before(document.createElement('br'));
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
 * Returns an array of url infos for url matched in the given string.
 *
 * @param {String} string
 * @returns {Array}
 */
export function getUrlsInfosInString(string) {
    let infos = [],
        match;
    while ((match = URL_REGEX_WITH_INFOS.exec(string))) {
        infos.push({
            url: match[2] ? match[0] : 'https://' + match[0],
            label: match[0],
            index: match.index,
            length: match[0].length,
        });
    }
    return infos;
}

// optimize: use the parent Oid to speed up detection
export function getOuid(node, optimize = false) {
    while (node && !isUnbreakable(node)) {
        if (node.ouid && optimize) return node.ouid;
        node = node.parentNode;
    }
    return node && node.oid;
}
/**
 * Returns whether the given node is a element that could be considered to be
 * removed by itself = self closing tags.
 *
 * @param {Node} node
 * @returns {boolean}
 */
const selfClosingElementTags = ['BR', 'IMG', 'INPUT'];
export function isVisibleEmpty(node) {
    return selfClosingElementTags.includes(node.nodeName);
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
        (!!element.closest('pre') ||
            getComputedStyle(element).getPropertyValue('white-space') === 'pre')
    );
}
/**
 * Returns whether the given string (or given text node value)
 * has at least one visible character or one non colapsed whitespace characters in it.
 */
const nonWhitespacesRegex = /[\S\u00A0]/;
export function isVisibleStr(value) {
    const str = typeof value === 'string' ? value : value.nodeValue;
    return nonWhitespacesRegex.test(str);
}
/**
 * @param {Node} node
 * @returns {boolean}
 */
export function isContentTextNode(node) {
    return node.nodeType === Node.TEXT_NODE && (isVisible(node) || isInPre(node));
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
 * @param {boolean} areBlocksAlwaysVisible
 * @returns {boolean}
 */
export function isVisible(node, areBlocksAlwaysVisible = true) {
    if (!node) return false;
    if (node.nodeType === Node.TEXT_NODE) {
        return isVisibleTextNode(node);
    }
    if ((areBlocksAlwaysVisible && isBlock(node)) || isVisibleEmpty(node)) {
        return true;
    }
    return [...node.childNodes].some(n => isVisible(n));
}

function isVisibleTextNode(testedNode) {
    if (!testedNode.length) {
        return false;
    }
    if (isVisibleStr(testedNode)) {
        return true;
    }
    // The following assumes node is made entirely of whitespace and is not
    // preceded of followed by a block.
    // Find out contiguous preceding and following text nodes
    let preceding;
    let following;
    // Control variable to know whether the current node has been found
    let foundTestedNode;
    const currentNodeParentBlock = closestBlock(testedNode);
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
        }
    }
    while (following && /^[\n\t ]*$/.test(following.textContent)) {
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
    return !/^[\n\t ]*$/.test(preceding.textContent);
}

export function parentsGet(node, root = undefined) {
    const parents = [];
    while (node) {
        parents.unshift(node);
        if (node === root) {
            break;
        }
        node = node.parentNode;
    }
    return parents;
}

export function commonParentGet(node1, node2, root = undefined) {
    if (!node1 || !node2) {
        return null;
    }
    const n1p = parentsGet(node1, root);
    const n2p = parentsGet(node2, root);
    while (n1p.length > 1 && n1p[1] === n2p[1]) {
        n1p.shift();
        n2p.shift();
    }
    // Check  in case at least one of them is not in the DOM.
    return n1p[0] === n2p[0] ? n1p[0] : null;
}

export function getListMode(pnode) {
    if (pnode.tagName == 'OL') return 'OL';
    return pnode.classList.contains('o_checklist') ? 'CL' : 'UL';
}

export function createList(mode) {
    const node = document.createElement(mode == 'OL' ? 'OL' : 'UL');
    if (mode == 'CL') {
        node.classList.add('o_checklist');
    }
    return node;
}

export function insertListAfter(afterNode, mode, content = []) {
    const list = createList(mode);
    afterNode.after(list);
    list.append(
        ...content.map(c => {
            const li = document.createElement('LI');
            li.append(...[].concat(c));
            return li;
        }),
    );
    return list;
}

export function toggleClass(node, className) {
    node.classList.toggle(className);
    if (!node.className) {
        node.removeAttribute('class');
    }
}

/**
 * Returns whether or not the given node is a BR element which does not really
 * act as a line break, but as a placeholder for the cursor or to make some left
 * element (like a space) visible.
 *
 * @param {HTMLBRElement} brEl
 * @returns {boolean}
 */
export function isFakeLineBreak(brEl) {
    return !(getState(...rightPos(brEl), DIRECTIONS.RIGHT).cType & (CTGROUPS.INLINE | CTGROUPS.BR));
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
    if (isVisibleStr(blockEl.textContent)) {
        return false;
    }
    if (blockEl.querySelectorAll('br').length >= 2) {
        return false;
    }
    const nodes = blockEl.querySelectorAll('*');
    for (const node of nodes) {
        // There is no text and no double BR, the only thing that could make
        // this visible is a "visible empty" node like an image.
        if (node.nodeName != 'BR' && isVisibleEmpty(node)) {
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
    return (
        isEmptyBlock(blockEl) &&
        !blockEl.querySelector('br') &&
        blockEl.nodeName !== "IMG"
    );
}

/**
 * @param {string} [value]
 * @returns {boolean}
 */
export function isColorGradient(value) {
    // FIXME duplicated in @web_editor/utils.js
    return value && value.includes('-gradient(');
}

//------------------------------------------------------------------------------
// DOM Modification
//------------------------------------------------------------------------------

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
 * @param {DIRECTION} originalNodeSide Whether the original node ends up on left
 * or right after the split
 * @returns {number} The parentOffset if the cursor was between the two text
 *          node parts after the split.
 */
export function splitTextNode(textNode, offset, originalNodeSide = DIRECTIONS.RIGHT) {
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

/**
 * Split the given element at the given offset. The element will be removed in
 * the process so caution is advised in dealing with its reference. Returns a
 * tuple containing the new elements on both sides of the split.
 *
 * @param {Element} element
 * @param {number} offset
 * @returns {[Element, Element]}
 */
export function splitElement(element, offset) {
    const before = element.cloneNode();
    const after = element.cloneNode();
    let index = 0;
    for (const child of [...element.childNodes]) {
        index < offset ? before.appendChild(child) : after.appendChild(child);
        index++;
    }
    element.before(before);
    element.after(after);
    element.remove();
    return [before, after];
}

/**
 * Split around the given elements, until a given ancestor (included). Elements
 * will be removed in the process so caution is advised in dealing with their
 * references. Returns a tuple containing the new elements on both sides of the
 * split.
 *
 * @see splitElement
 * @param {Node[] | Node} elements
 * @param {Node} limitAncestor
 * @returns {[Node, Node]}
 */
export function splitAroundUntil(elements, limitAncestor) {
    elements = Array.isArray(elements) ? elements : [elements];
    let after = elements[elements.length - 1].nextSibling;
    let newUntil = limitAncestor;
    let beforeSplit, afterSplit;
    // Split up ancestors up to font
    while (after && after.parentElement !== limitAncestor) {
        afterSplit = splitElement(after.parentElement, childNodeIndex(after))[0];
        newUntil = afterSplit;
        after = newUntil.nextSibling;
    }
    if (after) {
        afterSplit = splitElement(limitAncestor, childNodeIndex(after))[0];
        limitAncestor = afterSplit;
    }
    let before = elements[0].previousSibling;
    while (before && before.parentElement !== limitAncestor) {
        beforeSplit = splitElement(before.parentElement, childNodeIndex(before) + 1)[1];
        newUntil = beforeSplit;
        before = newUntil.previousSibling;
    }
    if (before) {
        beforeSplit = splitElement(limitAncestor, childNodeIndex(before) + 1)[1];
    }
    return [beforeSplit, afterSplit];
}

export function insertText(sel, content) {
    if (sel.anchorNode.nodeType === Node.TEXT_NODE) {
        const pos = [sel.anchorNode.parentElement, splitTextNode(sel.anchorNode, sel.anchorOffset)];
        setSelection(...pos, ...pos, false);
    }
    const txt = document.createTextNode(content || '#');
    const restore = prepareUpdate(sel.anchorNode, sel.anchorOffset);
    sel.getRangeAt(0).insertNode(txt);
    restore();
    setSelection(...boundariesOut(txt), false);
    return txt;
}

/**
 * Remove node from the DOM while preserving their contents if any.
 *
 * @param {Node} node
 * @returns {Node[]}
 */
export function unwrapContents(node) {
    const contents = [...node.childNodes];
    for (const child of contents) {
        node.parentNode.insertBefore(child, node);
    }
    node.parentNode.removeChild(node);
    return contents;
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
    const fillers = {};
    const blockEl = closestBlock(el);
    if (isShrunkBlock(blockEl)) {
        const br = document.createElement('br');
        blockEl.appendChild(br);
        fillers.br = br;
    }
    if (
        !el.textContent.length &&
        !isBlock(el) &&
        el.nodeName !== 'BR' &&
        !el.hasAttribute("oe-zws-empty-inline")
    ) {
        // As soon as there is actual content in the node, the zero-width space
        // is removed by the sanitize function.
        const zws = document.createTextNode('\u200B');
        el.appendChild(zws);
        el.setAttribute("oe-zws-empty-inline", "");
        fillers.zws = zws;
        const previousSibling = el.previousSibling;
        if (previousSibling && previousSibling.nodeName === "BR") {
            previousSibling.remove();
        }
        setSelection(zws, 0, zws, 0);
    }
    return fillers;
}
/**
 * Takes a selection (assumed to be collapsed) and insert a zero-width space at
 * its anchor point. Then, select that zero-width space.
 *
 * @param {Selection} selection
 * @returns {Node} the inserted zero-width space
 */
export function insertAndSelectZws(selection) {
    const offset = selection.anchorOffset;
    const zws = insertText(selection, '\u200B');
    splitTextNode(zws, offset);
    selection.getRangeAt(0).selectNode(zws);
    return zws;
}
/**
 * Removes the given node if invisible and all its invisible ancestors.
 *
 * @param {Node} node
 * @returns {Node} the first visible ancestor of node (or itself)
 */
export function clearEmpty(node) {
    while (!isVisible(node)) {
        const toRemove = node;
        node = node.parentNode;
        toRemove.remove();
    }
    return node;
}

export function setTagName(el, newTagName) {
    if (el.tagName === newTagName) {
        return el;
    }
    var n = document.createElement(newTagName);
    var attr = el.attributes;
    for (var i = 0, len = attr.length; i < len; ++i) {
        n.setAttribute(attr[i].name, attr[i].value);
    }
    while (el.firstChild) {
        n.append(el.firstChild);
    }
    if (el.tagName === 'LI') {
        el.append(n);
    } else {
        el.parentNode.replaceChild(n, el);
    }
    return n;
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
    endIndex = sourceEl.childNodes.length,
) {
    if (selfClosingElementTags.includes(destinationEl.nodeName)) {
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
            ...rightPos(sourceEl.childNodes[endIndex - 1]),
        );
        const fragment = document.createDocumentFragment();
        nodes.forEach(node => fragment.appendChild(node));
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
    const firstNode = nodes.find(node => !!node.parentNode);
    return firstNode ? leftPos(firstNode) : [destinationEl, destinationOffset];
}

//------------------------------------------------------------------------------
// Prepare / Save / Restore state utilities
//------------------------------------------------------------------------------

/**
 * Any editor command is applied to a selection (collapsed or not). After the
 * command, the content type on the selection boundaries, in both direction,
 * should be preserved (some whitespace should disappear as went from collapsed
 * to non collapsed, or converted to &nbsp; as went from non collapsed to
 * collapsed, there also <br> to remove/duplicate, etc).
 *
 * This function returns a callback which allows to do that after the command
 * has been done.
 *
 * Note: the method has been made generic enough to work with non-collapsed
 * selection but can be used for an unique cursor position.
 *
 * @param {HTMLElement} el
 * @param {number} offset
 * @param {...(HTMLElement|number)} args - argument 1 and 2 can be repeated for
 *     multiple preparations with only one restore callback returned. Note: in
 *     that case, the positions should be given in the document node order.
 * @returns {function}
 */
export function prepareUpdate(...args) {
    const positions = [...args];

    // Check the state in each direction starting from each position.
    const restoreData = [];
    let el, offset;
    while (positions.length) {
        // Note: important to get the positions in reverse order to restore
        // right side before left side.
        offset = positions.pop();
        el = positions.pop();
        const left = getState(el, offset, DIRECTIONS.LEFT);
        restoreData.push(left);
        restoreData.push(getState(el, offset, DIRECTIONS.RIGHT, left.cType));
    }

    // Create the callback that will be able to restore the state in each
    // direction wherever the node in the opposite direction has landed.
    return function restoreStates() {
        for (const data of restoreData) {
            restoreState(data);
        }
    };
}
/**
 * Retrieves the "state" from a given position looking at the given direction.
 * The "state" is the type of content. The functions also returns the first
 * meaninful node looking in the opposite direction = the first node we trust
 * will not disappear if a command is played in the given direction.
 *
 * Note: only work for in-between nodes positions. If the position is inside a
 * text node, first split it @see splitTextNode.
 *
 * @param {HTMLElement} el
 * @param {number} offset
 * @param {number} direction @see DIRECTIONS.LEFT @see DIRECTIONS.RIGHT
 * @param {CTYPES} leftCType
 * @returns {Object}
 */
export function getState(el, offset, direction, leftCType) {
    const leftDOMPath = leftLeafOnlyNotBlockPath;
    const rightDOMPath = rightLeafOnlyNotBlockPath;

    let domPath;
    let inverseDOMPath;
    let expr;
    const reasons = [];
    if (direction === DIRECTIONS.LEFT) {
        domPath = leftDOMPath(el, offset, reasons);
        inverseDOMPath = rightDOMPath(el, offset);
        expr = /[^\S\u00A0]$/;
    } else {
        domPath = rightDOMPath(el, offset, reasons);
        inverseDOMPath = leftDOMPath(el, offset);
        expr = /^[^\S\u00A0]/;
    }

    // TODO I think sometimes, the node we have to consider as the
    // anchor point to restore the state is not the first one of the inverse
    // path (like for example, empty text nodes that may disappear
    // after the command so we would not want to get those ones).
    const boundaryNode = inverseDOMPath.next().value;

    // We only traverse through deep inline nodes. If we cannot find a
    // meanfingful state between them, that means we hit a block.
    let cType = undefined;

    // Traverse the DOM in the given direction to check what type of content
    // there is.
    let lastSpace = null;
    for (const node of domPath) {
        if (node.nodeType === Node.TEXT_NODE) {
            const value = node.nodeValue;
            // If we hit a text node, the state depends on the path direction:
            // any space encountered backwards is a visible space if we hit
            // visible content afterwards. If going forward, spaces are only
            // visible if we have content backwards.
            if (direction === DIRECTIONS.LEFT) {
                if (isVisibleStr(value)) {
                    cType = lastSpace || expr.test(value) ? CTYPES.SPACE : CTYPES.CONTENT;
                    break;
                }
                if (value.length) {
                    lastSpace = node;
                }
            } else {
                leftCType = leftCType || getState(el, offset, DIRECTIONS.LEFT).cType;
                if (expr.test(value)) {
                    const rct = isVisibleStr(value)
                        ? CTYPES.CONTENT
                        : getState(...rightPos(node), DIRECTIONS.RIGHT).cType;
                    cType =
                        leftCType & CTYPES.CONTENT && rct & (CTYPES.CONTENT | CTYPES.BR)
                            ? CTYPES.SPACE
                            : rct;
                    break;
                }
                if (isVisibleStr(value)) {
                    cType = CTYPES.CONTENT;
                    break;
                }
            }
        } else if (node.nodeName === 'BR') {
            cType = CTYPES.BR;
            break;
        } else if (isVisible(node)) {
            // E.g. an image
            cType = CTYPES.CONTENT;
            break;
        }
    }

    if (cType === undefined) {
        cType = reasons.includes(PATH_END_REASONS.BLOCK_HIT)
            ? CTYPES.BLOCK_OUTSIDE
            : CTYPES.BLOCK_INSIDE;
    }

    return {
        node: boundaryNode,
        direction: direction,
        cType: cType, // Short for contentType
    };
}
const priorityRestoreStateRules = [
    // Each entry is a list of two objects, with each key being optional (the
    // more key-value pairs, the bigger the priority).
    // {direction: ..., cType1: ..., cType2: ...}
    // ->
    // {spaceVisibility: (false|true), brVisibility: (false|true)}
    [
        // Replace a space by &nbsp; when it was not collapsed before and now is
        // collapsed (one-letter word removal for example).
        { cType1: CTYPES.CONTENT, cType2: CTYPES.SPACE | CTGROUPS.BLOCK },
        { spaceVisibility: true },
    ],
    [
        // Replace a space by &nbsp; when it was content before and now it is
        // a BR.
        { direction: DIRECTIONS.LEFT, cType1: CTGROUPS.INLINE, cType2: CTGROUPS.BR },
        { spaceVisibility: true },
    ],
    [
        // Replace a space by &nbsp; when it was visible thanks to a BR which
        // is now gone.
        { direction: DIRECTIONS.RIGHT, cType1: CTGROUPS.BR, cType2: CTYPES.SPACE | CTGROUPS.BLOCK },
        { spaceVisibility: true },
    ],
    [
        // Remove all collapsed spaces when a space is removed.
        { cType1: CTYPES.SPACE },
        { spaceVisibility: false },
    ],
    [
        // Remove spaces once the preceeding BR is removed
        { direction: DIRECTIONS.LEFT, cType1: CTGROUPS.BR },
        { spaceVisibility: false },
    ],
    [
        // Remove space before block once content is put after it (otherwise it
        // would become visible).
        { cType1: CTGROUPS.BLOCK, cType2: CTGROUPS.INLINE | CTGROUPS.BR },
        { spaceVisibility: false },
    ],
    [
        // Duplicate a BR once the content afterwards disappears
        { direction: DIRECTIONS.RIGHT, cType1: CTGROUPS.INLINE, cType2: CTGROUPS.BLOCK },
        { brVisibility: true },
    ],
    [
        // Remove a BR at the end of a block once inline content is put after
        // it (otherwise it would act as a line break).
        {
            direction: DIRECTIONS.RIGHT,
            cType1: CTGROUPS.BLOCK,
            cType2: CTGROUPS.INLINE | CTGROUPS.BR,
        },
        { brVisibility: false },
    ],
    [
        // Remove a BR once the BR that preceeds it is now replaced by
        // content (or if it was a BR at the start of a block which now is
        // a trailing BR).
        {
            direction: DIRECTIONS.LEFT,
            cType1: CTGROUPS.BR | CTGROUPS.BLOCK,
            cType2: CTGROUPS.INLINE,
        },
        { brVisibility: false, extraBRRemovalCondition: brNode => isFakeLineBreak(brNode) },
    ],
];
function restoreStateRuleHashCode(direction, cType1, cType2) {
    return `${direction}-${cType1}-${cType2}`;
}
const allRestoreStateRules = (function () {
    const map = new Map();

    const keys = ['direction', 'cType1', 'cType2'];
    for (const direction of Object.values(DIRECTIONS)) {
        for (const cType1 of Object.values(CTYPES)) {
            for (const cType2 of Object.values(CTYPES)) {
                const rule = { direction: direction, cType1: cType1, cType2: cType2 };

                // Search for the rules which match whatever their priority
                const matchedRules = [];
                for (const entry of priorityRestoreStateRules) {
                    let priority = 0;
                    for (const key of keys) {
                        const entryKeyValue = entry[0][key];
                        if (entryKeyValue !== undefined) {
                            if (
                                typeof entryKeyValue === 'boolean'
                                    ? rule[key] === entryKeyValue
                                    : rule[key] & entryKeyValue
                            ) {
                                priority++;
                            } else {
                                priority = -1;
                                break;
                            }
                        }
                    }
                    if (priority >= 0) {
                        matchedRules.push([priority, entry[1]]);
                    }
                }

                // Create the final rule by merging found rules by order of
                // priority
                const finalRule = {};
                for (let p = 0; p <= keys.length; p++) {
                    for (const entry of matchedRules) {
                        if (entry[0] === p) {
                            Object.assign(finalRule, entry[1]);
                        }
                    }
                }

                // Create an unique identifier for the set of values
                // direction - state 1 - state2 to add the rule in the map
                const hashCode = restoreStateRuleHashCode(direction, cType1, cType2);
                map.set(hashCode, finalRule);
            }
        }
    }

    return map;
})();
/**
 * Restores the given state starting before the given while looking in the given
 * direction.
 *
 * @param {Object} prevStateData @see getState
 */
export function restoreState(prevStateData) {
    const { node, direction, cType: cType1 } = prevStateData;
    if (!node || !node.parentNode) {
        // FIXME sometimes we want to restore the state starting from a node
        // which has been removed by another restoreState call... Not sure if
        // it is a problem or not, to investigate.
        return;
    }
    const [el, offset] = direction === DIRECTIONS.LEFT ? leftPos(node) : rightPos(node);
    const { cType: cType2 } = getState(el, offset, direction);

    /**
     * Knowing the old state data and the new state data, we know if we have to
     * do something or not, and what to do.
     */
    const ruleHashCode = restoreStateRuleHashCode(direction, cType1, cType2);
    const rule = allRestoreStateRules.get(ruleHashCode);
    if (Object.values(rule).filter(x => x !== undefined).length) {
        const inverseDirection = direction === DIRECTIONS.LEFT ? DIRECTIONS.RIGHT : DIRECTIONS.LEFT;
        enforceWhitespace(el, offset, inverseDirection, rule);
    }
}
/**
 * Enforces the whitespace and BR visibility in the given direction starting
 * from the given position.
 *
 * @param {HTMLElement} el
 * @param {number} offset
 * @param {number} direction @see DIRECTIONS.LEFT @see DIRECTIONS.RIGHT
 * @param {Object} rule
 * @param {boolean} [rule.spaceVisibility]
 * @param {boolean} [rule.brVisibility]
 */
export function enforceWhitespace(el, offset, direction, rule) {
    let domPath;
    let expr;
    if (direction === DIRECTIONS.LEFT) {
        domPath = leftLeafOnlyNotBlockPath(el, offset);
        expr = /[^\S\u00A0]+$/;
    } else {
        domPath = rightLeafOnlyNotBlockPath(el, offset);
        expr = /^[^\S\u00A0]+/;
    }

    const invisibleSpaceTextNodes = [];
    let foundVisibleSpaceTextNode = null;
    for (const node of domPath) {
        if (node.nodeName === 'BR') {
            if (rule.brVisibility === undefined) {
                break;
            }
            if (rule.brVisibility) {
                node.before(document.createElement('br'));
            } else {
                if (!rule.extraBRRemovalCondition || rule.extraBRRemovalCondition(node)) {
                    node.remove();
                }
            }
            break;
        } else if (node.nodeType === Node.TEXT_NODE && !isInPre(node)) {
            if (expr.test(node.nodeValue)) {
                // If we hit spaces going in the direction, either they are in a
                // visible text node and we have to change the visibility of
                // those spaces, or it is in an invisible text node. In that
                // last case, we either remove the spaces if there are spaces in
                // a visible text node going further in the direction or we
                // change the visiblity or those spaces.
                if (isVisibleStr(node)) {
                    foundVisibleSpaceTextNode = node;
                    break;
                } else {
                    invisibleSpaceTextNodes.push(node);
                }
            } else if (isVisibleStr(node)) {
                break;
            }
        }
    }

    if (rule.spaceVisibility === undefined) {
        return;
    }
    if (!rule.spaceVisibility) {
        for (const node of invisibleSpaceTextNodes) {
            // Empty and not remove to not mess with offset-based positions in
            // commands implementation, also remove non-block empty parents.
            node.nodeValue = '';
            const ancestorPath = closestPath(node.parentNode);
            let toRemove = null;
            for (const pNode of ancestorPath) {
                if (toRemove) {
                    toRemove.remove();
                }
                if (pNode.childNodes.length === 1 && !isBlock(pNode)) {
                    pNode.after(node);
                    toRemove = pNode;
                } else {
                    break;
                }
            }
        }
    }
    const spaceNode = foundVisibleSpaceTextNode || invisibleSpaceTextNodes[0];
    if (spaceNode) {
        let spaceVisibility = rule.spaceVisibility;
        // In case we are asked to replace the space by a &nbsp;, disobey and
        // do the opposite if that space is currently not visible
        // TODO I'd like this to not be needed, it feels wrong...
        if (
            spaceVisibility &&
            !foundVisibleSpaceTextNode &&
            getState(...rightPos(spaceNode), DIRECTIONS.RIGHT).cType & CTGROUPS.BLOCK
        ) {
            spaceVisibility = false;
        }
        spaceNode.nodeValue = spaceNode.nodeValue.replace(expr, spaceVisibility ? '\u00A0' : '');
    }
}

export function rgbToHex(rgb = '') {
    return (
        '#' +
        (rgb.match(/\d{1,3}/g) || [])
            .map(x => {
                x = parseInt(x).toString(16);
                return x.length === 1 ? '0' + x : x;
            })
            .join('')
    );
}

export function getRangePosition(el, document, options = {}) {
    const selection = document.getSelection();
    if (!selection.isCollapsed || !selection.rangeCount) return;
    const range = selection.getRangeAt(0);

    const marginRight = options.marginRight || 20;
    const marginBottom = options.marginBottom || 20;
    const marginTop = options.marginTop || 10;
    const marginLeft = options.marginLeft || 10;

    let offset;
    if (range.endOffset - 1 > 0) {
        const clonedRange = range.cloneRange();
        clonedRange.setStart(range.endContainer, range.endOffset - 1);
        clonedRange.setEnd(range.endContainer, range.endOffset);
        const rect = clonedRange.getBoundingClientRect();
        offset = { height: rect.height, left: rect.left + rect.width, top: rect.top };
        clonedRange.detach();
    }

    if (!offset || offset.heigh === 0) {
        const clonedRange = range.cloneRange();
        const shadowCaret = document.createTextNode('|');
        clonedRange.insertNode(shadowCaret);
        clonedRange.selectNode(shadowCaret);
        const rect = clonedRange.getBoundingClientRect();
        offset = { height: rect.height, left: rect.left, top: rect.top };
        shadowCaret.remove();
        clonedRange.detach();
    }

    const leftMove = Math.max(0, offset.left + el.offsetWidth + marginRight - window.innerWidth);
    if (leftMove && offset.left - leftMove > marginLeft) {
        offset.left -= leftMove;
    } else if (offset.left - leftMove < marginLeft) {
        offset.left = marginLeft;
    }

    if (
        offset.top - marginTop + offset.height + el.offsetHeight > window.innerHeight &&
        offset.top - el.offsetHeight - marginBottom > 0
    ) {
        offset.top -= el.offsetHeight;
    } else {
        offset.top += offset.height;
    }

    if (offset) {
        offset.top += window.scrollY;
        offset.left += window.scrollX;
    }

    return offset;
}

export const isNotEditableNode = node =>
    node.getAttribute &&
    node.getAttribute('contenteditable') &&
    node.getAttribute('contenteditable').toLowerCase() === 'false';

export const leftLeafFirstPath = createDOMPathGenerator(DIRECTIONS.LEFT);
export const leftLeafOnlyNotBlockPath = createDOMPathGenerator(DIRECTIONS.LEFT, {
    leafOnly: true,
    stopTraverseFunction: isBlock,
    stopFunction: isBlock,
});
export const leftLeafOnlyInScopeNotBlockNoEditablePath = createDOMPathGenerator(DIRECTIONS.LEFT, {
    leafOnly: true,
    inScope: true,
    stopTraverseFunction: node => isNotEditableNode(node) || isBlock(node),
    stopFunction: node => isNotEditableNode(node) || isBlock(node),
});

export const rightLeafOnlyNotBlockPath = createDOMPathGenerator(DIRECTIONS.RIGHT, {
    leafOnly: true,
    stopTraverseFunction: isBlock,
    stopFunction: isBlock,
});

export const rightLeafOnlyPathNotBlockNotEditablePath = createDOMPathGenerator(DIRECTIONS.RIGHT, {
    leafOnly: true,
});
export const rightLeafOnlyInScopeNotBlockPath = createDOMPathGenerator(DIRECTIONS.RIGHT, {
    leafOnly: true,
    inScope: true,
    stopTraverseFunction: isBlock,
    stopFunction: isBlock,
});
export const rightLeafOnlyNotBlockNotEditablePath = createDOMPathGenerator(DIRECTIONS.RIGHT, {
    leafOnly: true,
    stopTraverseFunction: node => isNotEditableNode(node) || isBlock(node),
    stopFunction: node => isBlock(node) && !isNotEditableNode(node),
});
//------------------------------------------------------------------------------
// Miscelaneous
//------------------------------------------------------------------------------
export function peek(arr) {
    return arr[arr.length - 1];
}
