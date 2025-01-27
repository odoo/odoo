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
export function ctypeToString(ctype) {
    return Object.keys(CTYPES).find((key) => CTYPES[key] === ctype);
}
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

const urlRegexBase = `|(?:www.))[-a-zA-Z0-9@:%._\\+~#=]{2,256}\\.[a-zA-Z][a-zA-Z0-9]{1,62}|(?:[-a-zA-Z0-9@:%._\\+~#=]{2,256}\\.(?:${tldWhitelist.join('|')})\\b))(?:(?:[/?#])[^\\s]*[^!.,})\\]'"\\s]|(?:[^!(){}.,[\\]'"\\s]+))?`;
const httpCapturedRegex= `(https?:\\/\\/)`;

export const URL_REGEX = new RegExp(`((?:(?:${httpCapturedRegex}${urlRegexBase})`, 'i');
export const YOUTUBE_URL_GET_VIDEO_ID =
    /^(?:(?:https?:)?\/\/)?(?:(?:www|m)\.)?(?:youtube\.com|youtu\.be)(?:\/(?:[\w-]+\?v=|embed\/|v\/)?)([^\s?&#]+)(?:\S+)?$/i;
export const EMAIL_REGEX = /^(mailto:)?[\w-.]+@(?:[\w-]+\.)+[\w-]{2,4}$/i;
export const PHONE_REGEX = /^(tel:(?:\/\/)?)?\+?[\d\s.\-()\/]{3,25}$/;

export const PROTECTED_BLOCK_TAG = ['TR','TD','TABLE','TBODY','UL','OL','LI'];

/**
 * Array of all the classes used by the editor to change the font size.
 *
 * Note: the Bootstrap "small" class is an exception, the editor does not allow
 * to set it but it did in the past and we want to remove it when applying an
 * override of the font-size.
 */
export const FONT_SIZE_CLASSES = ["display-1-fs", "display-2-fs", "display-3-fs", "display-4-fs", "h1-fs",
    "h2-fs", "h3-fs", "h4-fs", "h5-fs", "h6-fs", "base-fs", "o_small-fs", "small"];

/**
 * Array of all the classes used by the editor to change the text style.
 *
 * Note: the Bootstrap "small" class was actually part of "text style"
 * configuration in the past... but also of the "font size" configuration (see
 * FONT_SIZE_CLASSES). It should be mentioned here too.
 */
export const TEXT_STYLE_CLASSES = ["display-1", "display-2", "display-3", "display-4", "lead", "o_small", "small"];

const ZWNBSP_CHAR = '\ufeff';
export const ZERO_WIDTH_CHARS = ['\u200b', ZWNBSP_CHAR];
export const ZERO_WIDTH_CHARS_REGEX = new RegExp(`[${ZERO_WIDTH_CHARS.join('')}]`, 'g');

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
 * @see leftLeafOnlyInScopeNotBlockEditablePath
 * @see rightLeafOnlyNotBlockPath
 * @see rightLeafOnlyPathNotBlockNotEditablePath
 * @see rightLeafOnlyInScopeNotBlockEditablePath
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
 * Return the furthest uneditable parent of node contained within parentLimit.
 * @see deleteRange Used to guarantee that uneditables are fully contained in
 * the range (so that it is not possible to partially remove them)
 *
 * @param {Node} node
 * @param {Node} [parentLimit=undefined] non-inclusive furthest parent allowed
 * @returns {Node} uneditable parent if it exists
 */
export function getFurthestUneditableParent(node, parentLimit) {
    if (node === parentLimit || (parentLimit && !parentLimit.contains(node))) {
        return undefined;
    }
    let parent = node && node.parentElement;
    let nonEditableElement;
    while (parent && (!parentLimit || parent !== parentLimit)) {
        if (!parent.isContentEditable) {
            nonEditableElement = parent;
        }
        if (parent.oid === "root") {
            break;
        }
        parent = parent.parentElement;
    }
    return nonEditableElement;
}
/**
 * Returns the closest HTMLElement of the provided Node. If the predicate is a
 * string, returns the closest HTMLElement that match the predicate selector. If
 * the predicate is a function, returns the closest element that matches the
 * predicate. Any returned element will be contained within the editable.
 *
 * @param {Node} node
 * @param {string | Function} [predicate='*']
 * @returns {HTMLElement|null}
 */
export function closestElement(node, predicate = "*") {
    if (!node) return null;
    let element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    if (typeof predicate === 'function') {
        while (element && !predicate(element)) {
            element = element.parentElement;
        }
    } else {
        element = element?.closest(predicate);
    }

    return element?.closest('.odoo-editor-editable') && element;
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
 * Returns true if the given editable area contains a table with selected cells.
 *
 * @param {Element} editable
 * @returns {boolean}
 */
export function hasTableSelection(editable) {
    return !!editable.querySelector('.o_selected_table');
}
/**
 * Returns true if the given editable area contains a "valid" selection, by
 * which we mean a browser selection whose elements are defined, or a table with
 * selected cells.
 *
 * @param {Element} editable
 * @returns {boolean}
 */
export function hasValidSelection(editable) {
    return hasTableSelection(editable) || editable.ownerDocument.getSelection().rangeCount > 0;
}
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
    const editable = closestElement(node, '.odoo-editor-editable');
    let closest = closestElement(node);
    while (
        closest &&
        closest !== editable &&
        (isSelfClosingElement(node) || !closest.isContentEditable)
    ) {
        // Cannot put the cursor inside those elements, put it before if the
        // offset is 0 and the node is not empty, else after instead.
        [node, offset] = offset || !nodeSize(node) ? rightPos(node) : leftPos(node);
        closest = closestElement(node);
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
            const leftInlineNode = leftLeafOnlyInScopeNotBlockEditablePath(el, elOffset).next().value;
            let leftVisibleEmpty = false;
            if (leftInlineNode) {
                leftVisibleEmpty =
                    isSelfClosingElement(leftInlineNode) ||
                    !closestElement(leftInlineNode).isContentEditable;
                [node, offset] = leftVisibleEmpty
                    ? rightPos(leftInlineNode)
                    : endPos(leftInlineNode);
            }
            if (!leftInlineNode || leftVisibleEmpty) {
                const rightInlineNode = rightLeafOnlyInScopeNotBlockEditablePath(el, elOffset).next().value;
                if (rightInlineNode) {
                    const closest = closestElement(rightInlineNode);
                    const rightVisibleEmpty =
                        isSelfClosingElement(rightInlineNode) ||
                        !closest ||
                        !closest.isContentEditable;
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
export function insertSelectionChars(anchorNode, anchorOffset, focusNode, focusOffset, startChar='[', endChar=']') {
    // If the range characters have to be inserted within the same parent and
    // the anchor range character has to be before the focus range character,
    // the focus offset needs to be adapted to account for the first insertion.
    if (anchorNode === focusNode && anchorOffset <= focusOffset) {
        focusOffset += (focusNode.nodeType === Node.TEXT_NODE ? startChar.length : 1);
    }
    insertCharsAt(startChar, anchorNode, anchorOffset);
    insertCharsAt(endChar, focusNode, focusOffset);
}
/**
 * Log the contents of the given root, with the characters "[" and "]" around
 * the selection.
 *
 * @param {Element} root
 * @param {Object} [options={}]
 * @param {Selection} [options.selection] if undefined, the current selection is used.
 * @param {boolean} [options.doFormat] if true, the HTML is formatted.
 * @param {boolean} [options.includeOids] if true, the HTML is formatted.
 */
export function logSelection(root, options = {}) {
    const sel = options.selection || root.ownerDocument.getSelection();
    if (!root.contains(sel.anchorNode) || !root.contains(sel.focusNode)) {
        console.warn('The selection is not contained in the root.');
        return;
    }

    // Clone the root and its contents.
    let anchorClone, focusClone;
    const cloneTree = node => {
        const clone = node.cloneNode();
        if (options.includeOids) {
            clone.oid = node.oid;
        }
        anchorClone = anchorClone || (node === sel.anchorNode && clone);
        focusClone = focusClone || (node === sel.focusNode && clone);
        for (const child of node.childNodes || []) {
            clone.append(cloneTree(child));
        }
        return clone;
    }
    const rootClone = cloneTree(root);

    // Insert the selection characters.
    insertSelectionChars(anchorClone, sel.anchorOffset, focusClone, sel.focusOffset, '%c[%c', '%c]%c');

    // Remove information that is not useful for the log.
    rootClone.removeAttribute('data-last-history-steps');

    // Format the HTML by splitting and indenting to highlight the structure.
    if (options.doFormat) {
        const formatHtml = (node, spaces = 0) => {
            node.before(document.createTextNode('\n' + ' '.repeat(spaces)));
            for (const child of [...node.childNodes]) {
                formatHtml(child, spaces + 4);
            }
            if (node.nodeType !== Node.TEXT_NODE) {
                node.appendChild(document.createTextNode('\n' + ' '.repeat(spaces)));
            }
            if (options.includeOids) {
                if (node.nodeType === Node.TEXT_NODE) {
                    node.textContent += ` (${node.oid})`;
                } else {
                    node.setAttribute('oid', node.oid);
                }
            }
        }
        formatHtml(rootClone);
    }

    // Style and log the result.
    const selectionCharacterStyle = 'color: #75bfff; font-weight: 700;';
    const defaultStyle = 'color: inherit; font-weight: inherit;';
    console.log(
        makeZeroWidthCharactersVisible(rootClone.outerHTML),
        selectionCharacterStyle, defaultStyle, selectionCharacterStyle, defaultStyle,
    );
}
/**
 * Guarantee that the focus is on element or one of its children.
 *
 * A simple call to element.focus will change the editable context
 * if one of the parents of the current activeElement is not editable,
 * and the caret position will not be preserved, even if activeElement is
 * one of the subchildren of element. This is why the (re)focus is
 * only called when the current activeElement is not one of the
 * (sub)children of element.
 *
 * @param {Element} element should have the focus or a child with the focus
 */
 export function ensureFocus(element) {
    const activeElement = element.ownerDocument.activeElement;
    if (activeElement !== element && (!element.contains(activeElement) || !activeElement.isContentEditable)) {
        element.focus();
    }
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
        !anchorNode.parentElement ||
        !anchorNode.parentElement.closest('body') ||
        !focusNode ||
        !focusNode.parentElement ||
        !focusNode.parentElement.closest('body')
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
    try {
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
    } catch (e) {
        // Firefox throws NS_ERROR_FAILURE when setting selection on element
        // with contentEditable=false for no valid reason since non-editable
        // content are selectable by the user anyway.
        if (e.name !== 'NS_ERROR_FAILURE') {
            throw e;
        }
    }

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
    const selectedTableCells = editable.querySelectorAll('.o_selected_td');
    const document = editable.ownerDocument;
    if (!range) return [];
    const iterator = document.createNodeIterator(range.commonAncestorContainer);
    let node;
    do {
        node = iterator.nextNode();
    } while (node && node !== range.startContainer && !(selectedTableCells.length && node === selectedTableCells[0]));
    if (
        node &&
        !(selectedTableCells.length && node === selectedTableCells[0]) &&
        !range.collapsed &&
        node.nodeType === Node.ELEMENT_NODE &&
        node.childNodes.length &&
        range.startOffset &&
        node.childNodes[range.startOffset - 1].nodeName === "BR"
    ) {
        // Handle the cases:
        // <p>ab<br>[</p><p>cd</p>] => [p2, cd]
        // <p>ab<br>[<br>cd</p><p>ef</p>] => [br2, cd, p2, ef]
        const targetBr = node.childNodes[range.startOffset - 1];
        while (node != targetBr) {
            node = iterator.nextNode();
        }
        node = iterator.nextNode();
    }
    if (
        node &&
        !range.collapsed &&
        node === range.startContainer &&
        range.startOffset === nodeSize(node) &&
        node.nextSibling &&
        node.nextSibling.nodeName === "BR"
    ) {
        // Handle the case: <p>ab[<br>cd</p><p>ef</p>] => [br, cd, p2, ef]
        node = iterator.nextNode();
    }
    const traversedNodes = new Set([node, ...descendants(node)]);
    while (node && node !== range.endContainer) {
        node = iterator.nextNode();
        if (node) {
            const selectedTable = closestElement(node, '.o_selected_table');
            if (selectedTable) {
                for (const selectedTd of selectedTable.querySelectorAll('.o_selected_td')) {
                    traversedNodes.add(selectedTd);
                    descendants(selectedTd).forEach(descendant => traversedNodes.add(descendant));
                }
            } else if (
                !(
                    // Handle the case: [<p>ab</p><p>cd<br>]ef</p> => [ab, p2, cd, br]
                    node === range.endContainer &&
                    range.endOffset === 0 &&
                    !range.collapsed &&
                    node.previousSibling &&
                    node.previousSibling.nodeName === "BR"
                )
            ) {
                traversedNodes.add(node);
            }
        }
    }
    if (node) {
        // Handle the cases:
        // [<p>ab</p><p>cd<br>]</p> => [ab, p2, cd, br]
        // [<p>ab</p><p>cd<br>]<br>ef</p> => [ab, p2, cd, br1]
        for (const descendant of descendants(node)) {
            if (
                descendant.parentElement === node &&
                childNodeIndex(descendant) >= range.endOffset
            ) {
                break;
            }
            traversedNodes.add(descendant);
        }
    }
    return [...traversedNodes];
}
/**
 * Returns an array containing all the nodes fully contained in the selection.
 *
 * @param {Node} editable
 * @returns {Node[]}
 */
export function getSelectedNodes(editable) {
    const selectedTableCells = editable.querySelectorAll('.o_selected_td');
    const document = editable.ownerDocument;
    const sel = document.getSelection();
    if (!sel.rangeCount && !selectedTableCells.length) {
        return [];
    }
    const range = sel.getRangeAt(0);
    return [...new Set(getTraversedNodes(editable).flatMap(
        node => {
            const td = closestElement(node, '.o_selected_td');
            if (td) {
                return descendants(td);
            } else if (range.isPointInRange(node, 0) && range.isPointInRange(node, nodeSize(node))) {
                return node;
            } else {
                return [];
            }
        },
    ))];
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
    sel = sel || editable.parentElement && editable.ownerDocument.getSelection();
    if (sel && sel.isCollapsed && sel.anchorNode && sel.anchorNode.nodeName === "BR") {
        setSelection(sel.anchorNode.parentElement, childNodeIndex(sel.anchorNode));
    }
    range = range ? range.cloneRange() : sel && sel.rangeCount && sel.getRangeAt(0).cloneRange();
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
    // A selection spanning multiple nodes and ending at position 0 of a node,
    // like the one resulting from a triple click, is corrected so that it ends
    // at the last position of the previous node instead.
    const endLeaf = firstLeaf(end);
    const beforeEnd = endLeaf.previousSibling;
    const isInsideColumn = closestElement(end, '.o_text_columns')
    if (
        correctTripleClick &&
        !endOffset &&
        (start !== end || startOffset !== endOffset) &&
        (!beforeEnd ||
            (beforeEnd.nodeType === Node.TEXT_NODE &&
                !isVisibleTextNode(beforeEnd) &&
                !isZWS(beforeEnd))) &&
        !closestElement(endLeaf, 'table') &&
        !isInsideColumn
    ) {
        const previous = previousLeaf(endLeaf, editable, true);
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
        } catch {
            // Firefox yells not happy when setting selection on elem with contentEditable=false.
        }
        range = sel.getRangeAt(0);
    } else {
        range.setStart(start, startOffset);
        range.setEnd(end, endOffset);
    }
    return range;
}

export function getAdjacentCharacter(editable, side) {
    let { focusNode, focusOffset } = editable.ownerDocument.getSelection();
    const originalBlock = closestBlock(focusNode);
    let adjacentCharacter;
    while (!adjacentCharacter && focusNode) {
        if (side === 'previous') {
            adjacentCharacter = focusOffset > 0 && focusNode.textContent[focusOffset - 1];
        } else {
            adjacentCharacter = focusNode.textContent[focusOffset];
        }
        if (!adjacentCharacter) {
            if (side === 'previous') {
                focusNode = previousLeaf(focusNode, editable);
                focusOffset = focusNode && nodeSize(focusNode);
            } else {
                focusNode = nextLeaf(focusNode, editable);
                focusOffset = 0;
            }
            const characterIndex = side === 'previous' ? focusOffset - 1 : focusOffset;
            adjacentCharacter = focusNode && focusNode.textContent[characterIndex];
        }
    }
    return closestBlock(focusNode) === originalBlock ? adjacentCharacter : undefined;
}

function isZwnbsp(node) {
    return node.nodeType === Node.TEXT_NODE && node.textContent === '\ufeff';
}

function isTangible(node) {
    return isVisible(node) || isZwnbsp(node) || hasTangibleContent(node);
}

function hasTangibleContent(node) {
    return [...(node?.childNodes || [])].some(n => isTangible(n));
}

export function getDeepestPosition(node, offset) {
    let direction = DIRECTIONS.RIGHT;
    let next = node;
    while (next) {
        if (isTangible(next) || isZWS(next)) {
            // Valid node: update position then try to go deeper.
            if (next !== node) {
                [node, offset] = [next, direction ? 0 : nodeSize(next)];
            }
            // First switch direction to left if offset is at the end.
            direction = offset < node.childNodes.length;
            next = node.childNodes[direction ? offset : offset - 1];
        } else if (
            direction &&
            next.nextSibling &&
            closestBlock(node)?.contains(next.nextSibling)
        ) {
            // Invalid node: skip to next sibling (without crossing blocks).
            next = next.nextSibling;
        } else {
            // Invalid node: skip to previous sibling (without crossing blocks).
            direction = DIRECTIONS.LEFT;
            next = closestBlock(node)?.contains(next.previousSibling) && next.previousSibling;
        }
        // Avoid too-deep ranges inside self-closing elements like [BR, 0].
        next = !isSelfClosingElement(next) && next;
    }
    return [node, offset];
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
        return setSelection(...cursorPos, false);
    };
}

/**
 * Check if the selection starts inside given selector. This function can be
 * used as the `isDisabled` property of a command of the PowerBox to disable
 * a command in the given selectors.
 * @param {string}: comma separated string with all the desired selectors
 * @returns {boolean} true selector is within one of the selector
 * (if the command should be filtered)
 */
export function isSelectionInSelectors(selector) {
    let anchor = document.getSelection().anchorNode;
    if (anchor && anchor.nodeType && anchor.nodeType !== Node.ELEMENT_NODE) {
        anchor = anchor.parentElement;
    }
    if (anchor && closestElement(anchor, selector)) {
        return true;
    }
    return false;
}

export function getOffsetAndCharSize(nodeValue, offset, direction) {
    //We get the correct offset which corresponds to this offset
    // If direction is left it means we are coming from the right and
    // we want to get the end offset of the first element to the left
    // Example with LEFT direction:
    // <p>a \uD83D[offset]\uDE0D b</p> -> <p>a \uD83D\uDE0D[offset] b</p> and
    // size = 2 so delete backward will delete the whole emoji.
    // Example with Right direction:
    // <p>a \uD83D[offset]\uDE0D b</p> -> <p>a [offset]\uD83D\uDE0D b</p> and
    // size = 2 so delete forward will delete the whole emoji.
    const splittedNodeValue = [...nodeValue];
    let charSize = 1;
    let newOffset = offset;
    let currentSize = 0;
    for (const item of splittedNodeValue) {
        currentSize += item.length;
        if (currentSize >= offset) {
            newOffset = direction == DIRECTIONS.LEFT ? currentSize : currentSize - item.length;
            charSize = item.length;
            break;
        }
    }
    return [newOffset, charSize];
}

//------------------------------------------------------------------------------
// Format utils
//------------------------------------------------------------------------------

export const formatsSpecs = {
    italic: {
        tagName: 'em',
        isFormatted: isItalic,
        isTag: (node) => ['EM', 'I'].includes(node.tagName),
        hasStyle: (node) => Boolean(node.style && node.style['font-style']),
        addStyle: (node) => node.style['font-style'] = 'italic',
        addNeutralStyle: (node) => node.style['font-style'] = 'normal',
        removeStyle: (node) => removeStyle(node, 'font-style'),
    },
    bold: {
        tagName: 'strong',
        isFormatted: isBold,
        isTag: (node) => ['STRONG', 'B'].includes(node.tagName),
        hasStyle: (node) => Boolean(node.style && node.style['font-weight']),
        addStyle: (node) => node.style['font-weight'] = 'bolder',
        addNeutralStyle: (node) => {
            node.style['font-weight'] = 'normal'
        },
        removeStyle: (node) => removeStyle(node, 'font-weight'),
    },
    underline: {
        tagName: 'u',
        isFormatted: isUnderline,
        isTag: (node) => node.tagName === 'U',
        hasStyle: (node) => node.style && node.style['text-decoration-line'].includes('underline'),
        addStyle: (node) => node.style['text-decoration-line'] += ' underline',
        removeStyle: (node) => removeStyle(node, 'text-decoration-line', 'underline'),
    },
    strikeThrough: {
        tagName: 's',
        isFormatted: isStrikeThrough,
        isTag: (node) => node.tagName === 'S',
        hasStyle: (node) => node.style && node.style['text-decoration-line'].includes('line-through'),
        addStyle: (node) => node.style['text-decoration-line'] += ' line-through',
        removeStyle: (node) => removeStyle(node, 'text-decoration-line', 'line-through'),
    },
    fontSize: {
        isFormatted: isFontSize,
        hasStyle: (node) => node.style && node.style['font-size'],
        addStyle: (node, props) => {
            node.style['font-size'] = props.size;
            node.classList.remove(...FONT_SIZE_CLASSES);
        },
        removeStyle: (node) => removeStyle(node, 'font-size'),
    },
    setFontSizeClassName: {
        isFormatted: hasClass,
        hasStyle: (node, props) => FONT_SIZE_CLASSES
            .find(cls => node.classList.contains(cls)),
        addStyle: (node, props) => node.classList.add(props.className),
        removeStyle: (node) => {
            node.classList.remove(...FONT_SIZE_CLASSES, ...TEXT_STYLE_CLASSES);
            if (node.classList.length === 0) {
                node.removeAttribute("class");
            }
        },
    },
    switchDirection: {
        isFormatted: isDirectionSwitched,
    }
}

const removeStyle = (node, styleName, item) => {
    if (item) {
        const newStyle = node.style[styleName].split(' ').filter(x => x !== item).join(' ');
        node.style[styleName] = newStyle || null;
    } else {
        node.style[styleName] = null;
    }
    if (node.getAttribute('style') === '') {
        node.removeAttribute('style');
    }
};
const getOrCreateSpan = (node, ancestors) => {
    const span = ancestors.find((element) => element.tagName === 'SPAN' && element.isConnected);
    if (span) {
        return span;
    } else {
        const span = document.createElement('span');
        node.after(span);
        span.append(node);
        return span;
    }
}
const removeFormat = (node, formatSpec) => {
    node = closestElement(node);
    if (formatSpec.hasStyle(node)) {
        formatSpec.removeStyle(node);
        if (['SPAN', 'FONT'].includes(node.tagName) && !node.getAttributeNames().length) {
            return unwrapContents(node);
        }
    }

    if (formatSpec.isTag && formatSpec.isTag(node)) {
        const attributesNames = node.getAttributeNames().filter((name)=> {
            return name !== 'data-oe-zws-empty-inline';
        });
        if (attributesNames.length) {
            // Change tag name
            const newNode = document.createElement('span');
            while (node.firstChild) {
                newNode.appendChild(node.firstChild);
            }
            for (let index = node.attributes.length - 1; index >= 0; --index) {
                newNode.attributes.setNamedItem(node.attributes[index].cloneNode());
            }
            node.parentNode.replaceChild(newNode, node);
        } else {
            unwrapContents(node);
        }
    }
}

export const formatSelection = (editor, formatName, {applyStyle, formatProps} = {}) => {
    const selection = editor.document.getSelection();
    let direction
    let wasCollapsed;
    if (editor.editable.querySelector('.o_selected_td')) {
        direction = DIRECTIONS.RIGHT;
    } else {
        if (!selection.rangeCount) return;
        wasCollapsed = selection.getRangeAt(0).collapsed;

        direction = getCursorDirection(selection.anchorNode, selection.anchorOffset, selection.focusNode, selection.focusOffset);
    }
    getDeepRange(editor.editable, { splitText: true, select: true, correctTripleClick: true });

    if (typeof applyStyle === 'undefined') {
        applyStyle = !isSelectionFormat(editor.editable, formatName);
    }

    let zws;
    if (wasCollapsed) {
        if (selection.anchorNode.nodeType === Node.TEXT_NODE && selection.anchorNode.textContent === '\u200b') {
            zws = selection.anchorNode;
            selection.getRangeAt(0).selectNode(zws);
        } else {
            zws = insertAndSelectZws(selection);
        }
        getDeepRange(editor.editable, { splitText: true, select: true, correctTripleClick: true });
    }

    const selectedNodes = getSelectedNodes(editor.editable).filter(
        (n) =>
            ((n.nodeType === Node.TEXT_NODE && (isVisibleTextNode(n) || isZWS(n))) ||
                n.nodeName === "BR") &&
            closestElement(n).isContentEditable
    );

    const selectedFieldNodes = new Set(getSelectedNodes(editor.editable)
            .map(n =>closestElement(n, "*[t-field],*[t-out],*[t-esc]"))
            .filter(Boolean));

    const formatSpec = formatsSpecs[formatName];
    for (const node of selectedNodes) {
        const inlineAncestors = [];
        let currentNode = node;
        let parentNode = node.parentElement;

        // Remove the format on all inline ancestors until a block or an element
        // with a class that is not related to font size (in case the formatting
        // comes from the class).
        while (
            parentNode && !isBlock(parentNode) &&
            !isUnbreakable(parentNode) && !isUnbreakable(currentNode) &&
            (parentNode.classList.length === 0 ||
                [...parentNode.classList].every(cls => FONT_SIZE_CLASSES.includes(cls)))
        ) {
            const isUselessZws = parentNode.tagName === 'SPAN' &&
                parentNode.hasAttribute('data-oe-zws-empty-inline') &&
                parentNode.getAttributeNames().length === 1;

            if (isUselessZws) {
                unwrapContents(parentNode);
            } else {
                const newLastAncestorInlineFormat = splitAroundUntil(currentNode, parentNode);
                removeFormat(newLastAncestorInlineFormat, formatSpec);
                if (newLastAncestorInlineFormat.isConnected) {
                    inlineAncestors.push(newLastAncestorInlineFormat);
                    currentNode = newLastAncestorInlineFormat;
                }
            }

            parentNode = currentNode.parentElement;
        }

        const firstBlockOrClassHasFormat = formatSpec.isFormatted(parentNode, formatProps);
        if (firstBlockOrClassHasFormat && !applyStyle) {
            formatSpec.addNeutralStyle && formatSpec.addNeutralStyle(getOrCreateSpan(node, inlineAncestors));
        } else if (!firstBlockOrClassHasFormat && applyStyle) {
            const tag = formatSpec.tagName && document.createElement(formatSpec.tagName);
            if (tag) {
                node.after(tag);
                tag.append(node);

                if (!formatSpec.isFormatted(tag, formatProps)) {
                    tag.after(node);
                    tag.remove();
                    formatSpec.addStyle(getOrCreateSpan(node, inlineAncestors), formatProps);
                }
            } else if (formatName !== 'fontSize' || formatProps.size !== undefined) {
                formatSpec.addStyle(getOrCreateSpan(node, inlineAncestors), formatProps);
            }
        }
    }

    for (const selectedFieldNode of selectedFieldNodes) {
        if (applyStyle) {
            formatSpec.addStyle(selectedFieldNode, formatProps);
        } else {
            formatSpec.removeStyle(selectedFieldNode);
        }
    }

    if (zws) {
        const siblings = [...zws.parentElement.childNodes];
        if (
            !isBlock(zws.parentElement) &&
            selectedNodes.includes(siblings[0]) &&
            selectedNodes.includes(siblings[siblings.length - 1])
        ) {
            zws.parentElement.setAttribute('data-oe-zws-empty-inline', '');
        } else {
            const span = document.createElement('span');
            span.setAttribute('data-oe-zws-empty-inline', '');
            zws.before(span);
            span.append(zws);
        }
    }
    if (selectedNodes.length === 1 && selectedNodes[0].textContent === '\u200B') {
        setSelection(selectedNodes[0], 0);
    } else if (selectedNodes.length) {
        const firstNode = selectedNodes[0];
        const lastNode = selectedNodes[selectedNodes.length - 1];
        if (direction === DIRECTIONS.RIGHT) {
            setSelection(firstNode, 0, lastNode, lastNode.length, false);
        } else {
            setSelection(lastNode, lastNode.length, firstNode, 0, false);
        }
    }
}
export const isLinkEligibleForZwnbsp = (editable, link) => {
    return link.isContentEditable && editable.contains(link) && !(
        [link, ...link.querySelectorAll('*')].some(el => el.nodeName === 'IMG' || isBlock(el)) ||
        link.matches('nav a, a.nav-link')
    );
}
/**
 * Take a link and pad it with non-break zero-width spaces to ensure that it is
 * always possible to place the cursor at its inner and outer edges.
 *
 * @param {HTMLElement} editable
 * @param {HTMLAnchorElement} link
 */
export const padLinkWithZws = (editable, link) => {
    if (!isLinkEligibleForZwnbsp(editable, link)) {
        // Only add the ZWNBSP for simple (possibly styled) text links, and
        // never in a nav.
        return;
    }
    const selection = editable.ownerDocument.getSelection() || {};
    const { anchorOffset, focusOffset } = selection;
    let extraAnchorOffset = 0;
    let extraFocusOffset = 0;
    if (!link.textContent.startsWith('\uFEFF')) {
        if (selection.anchorNode === link && anchorOffset) {
            extraAnchorOffset += 1;
        }
        if (selection.focusNode === link && focusOffset) {
            extraFocusOffset += 1;
        }
        link.prepend(document.createTextNode('\uFEFF'));
    }
    if (!link.textContent.endsWith('\uFEFF')) {
        if (selection.anchorNode === link && anchorOffset + extraAnchorOffset === nodeSize(link)) {
            extraAnchorOffset += 1;
        }
        if (selection.focusNode === link && focusOffset + extraFocusOffset === nodeSize(link)) {
            extraFocusOffset += 1;
        }
        link.append(document.createTextNode('\uFEFF'));
    }
    const linkIndex = childNodeIndex(link);
    if (!(link.previousSibling && link.previousSibling.textContent.endsWith('\uFEFF'))) {
        if (selection.anchorNode === link.parentElement && anchorOffset + extraAnchorOffset > linkIndex) {
            extraAnchorOffset += 1;
        }
        if (selection.focusNode === link.parentElement && focusOffset + extraFocusOffset > linkIndex) {
            extraFocusOffset += 1;
        }
        link.before(document.createTextNode('\uFEFF'));
    }
    if (!(link.nextSibling && link.nextSibling.textContent.startsWith('\uFEFF'))) {
        if (selection.anchorNode === link.parentElement && anchorOffset + extraAnchorOffset > linkIndex + 1) {
            extraAnchorOffset += 1;
        }
        if (selection.focusNode === link.parentElement && focusOffset + extraFocusOffset > linkIndex + 1) {
            extraFocusOffset += 1;
        }
        link.after(document.createTextNode('\uFEFF'));
    }
    if (extraAnchorOffset || extraFocusOffset) {
        setSelection(
            selection.anchorNode, anchorOffset + extraAnchorOffset,
            selection.focusNode, focusOffset + extraFocusOffset,
        );
    }
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
    if (!node || node.nodeType !== Node.ELEMENT_NODE) {
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
    if (!node.isConnected) {
        return blockTagNames.includes(tagName);
    }
    // We won't call `getComputedStyle` more than once per node.
    let style = computedStyles.get(node);
    if (!style) {
        style = node.ownerDocument.defaultView?.getComputedStyle(node);
        computedStyles.set(node, style);
    }
    if (style?.display) {
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
        if (getComputedStyle(parent).textDecorationLine.includes('underline')) {
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
        if (getComputedStyle(parent).textDecorationLine.includes('line-through')) {
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
    return getComputedStyle(element)['font-size'] === props.size;
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
    const defaultDirection = editable.getAttribute('dir');
    return getComputedStyle(closestElement(node)).direction !== defaultDirection;
}
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
    const selectedNodes = getTraversedNodes(editable)
        .filter((n) => n.nodeType === Node.TEXT_NODE && n.nodeValue.replaceAll(ZWNBSP_CHAR, '').length);
    const isFormatted = formatsSpecs[format].isFormatted;
    return selectedNodes.length && selectedNodes.every(n => isFormatted(n, editable));
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
        ['TABLE', 'THEAD', 'TBODY', 'TFOOT', 'TR', 'TH', 'TD', 'SECTION', 'DIV'].includes(node.tagName) ||
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
                node.getAttribute('t-raw')) ||
                node.getAttribute('t-field')) ||
        node.matches(".oe_unbreakable, a.btn, a[role='tab'], a[role='button']")
    );
}

export function isUnremovable(node) {
    return (
        (node.nodeType !== Node.COMMENT_NODE && node.nodeType !== Node.ELEMENT_NODE && node.nodeType !== Node.TEXT_NODE) ||
        node.oid === 'root' ||
        (node.nodeType === Node.ELEMENT_NODE &&
            (node.classList.contains('o_editable') || node.getAttribute('t-set') || node.getAttribute('t-call'))) ||
        (node.classList && node.classList.contains('oe_unremovable')) ||
        (node.nodeName === 'SPAN' && node.parentElement && node.parentElement.getAttribute('data-oe-type') === 'monetary') ||
        (node.ownerDocument && node.ownerDocument.defaultWindow && !ancestors(node).find(ancestor => ancestor.oid === 'root')) // Node is in DOM but not in editable.
    );
}

export function containsUnbreakable(node) {
    if (!node) {
        return false;
    }
    return isUnbreakable(node) || containsUnbreakable(node.firstChild);
}

const iconTags = ['I', 'SPAN'];
const iconClasses = ['fa', 'fab', 'fad', 'far', 'oi'];
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
        iconClasses.some(cls => node.classList.contains(cls))
    );
}
export const ICON_SELECTOR = iconTags.map(tag => {
    return iconClasses.map(cls => {
        return `${tag}.${cls}`;
    }).join(', ');
}).join(', ');

/**
 * Return true if the given node is a zero-width breaking space (200b), false
 * otherwise. Note that this will return false for a zero-width NON-BREAK space
 * (feff)!
 *
 * @param {Node} node
 * @returns {boolean}
 */
export function isZWS(node) {
    return (
        node &&
        node.textContent === '\u200B'
    );
}
export function isEditorTab(node) {
    return (
        node &&
        (node.nodeName === 'SPAN') &&
        node.classList.contains('oe-tabs')
    );
}
export function isMediaElement(node) {
    return (
        isIconElement(node) ||
        (node.classList &&
            (node.classList.contains('o_image') || node.classList.contains('media_iframe_video')))
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
    const closestProtectedElement = closestElement(node, '[data-oe-protected]');
    if (closestProtectedElement) {
        return ["", "true"].includes(closestProtectedElement.dataset.oeProtected);
    }
    return false;
}

// https://developer.mozilla.org/en-US/docs/Glossary/Void_element
const VOID_ELEMENT_NAMES = ['AREA', 'BASE', 'BR', 'COL', 'EMBED', 'HR', 'IMG',
    'INPUT', 'KEYGEN', 'LINK', 'META', 'PARAM', 'SOURCE', 'TRACK', 'WBR'];

export function isArtificialVoidElement(node) {
    return isMediaElement(node) || node.nodeName === 'HR';
}

export function isNotAllowedContent(node) {
    return isArtificialVoidElement(node) || VOID_ELEMENT_NAMES.includes(node.nodeName);
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
    if (range) {
        const selectorInStartAncestors = closestElement(range.startContainer, selector);
        if (selectorInStartAncestors) {
            return selectorInStartAncestors;
        } else {
            const commonElementAncestor = closestElement(range.commonAncestorContainer);
            return commonElementAncestor && [...commonElementAncestor.querySelectorAll(selector)].find(
                node => range.intersectsNode(node),
            );
        }
    }
}

/**
 * Get the index of the given table row/cell.
 *
 * @private
 * @param {HTMLTableRowElement|HTMLTableCellElement} trOrTd
 * @returns {number}
 */
export function getRowIndex(trOrTd) {
    const tr = closestElement(trOrTd, 'tr');
    const trParent = tr && tr.parentElement;
    if (!trParent) {
        return -1;
    }
    const trSiblings = [...trParent.children].filter(child => child.nodeName === 'TR');
    return trSiblings.findIndex(child => child === tr);
}

/**
 * Get the index of the given table cell.
 *
 * @private
 * @param {HTMLTableCellElement} td
 * @returns {number}
 */
export function getColumnIndex(td) {
    const tdParent = td.parentElement;
    if (!tdParent) {
        return -1;
    }
    const tdSiblings = [...tdParent.children].filter(child => child.nodeName === 'TD' || child.nodeName === 'TH');
    return tdSiblings.findIndex(child => child === td);
}

// This is a list of "paragraph-related elements", defined as elements that
// behave like paragraphs.
export const paragraphRelatedElements = [
    'P',
    'H1',
    'H2',
    'H3',
    'H4',
    'H5',
    'H6',
    'PRE',
    'BLOCKQUOTE',
];

/**
 * Return true if the given node allows "paragraph-related elements".
 *
 * @see paragraphRelatedElements
 * @param {Node} node
 * @returns {boolean}
 */
export function allowsParagraphRelatedElements(node) {
    return isBlock(node) && !['P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6'].includes(node.nodeName);
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

// optimize: use the parent Oid to speed up detection
export function getOuid(node, optimize = false) {
    while (node && !isUnbreakable(node)) {
        if (node.ouid && optimize) return node.ouid;
        node = node.parentNode;
    }
    return node && node.oid;
}
/**
 * Returns true if the provided node can suport html content.
 *
 * @param {Node} node
 * @returns {boolean}
 */
export function isHtmlContentSupported(node) {
    return !closestElement(node, '[data-oe-model]:not([data-oe-field="arch"]):not([data-oe-type="html"]),[data-oe-translation-id]', true);
}
/**
 * Returns whether the given node is a element that could be considered to be
 * removed by itself = self closing tags.
 *
 * @param {Node} node
 * @returns {boolean}
 */
const selfClosingElementTags = ['BR', 'IMG', 'INPUT'];
export function isSelfClosingElement(node) {
    return node && selfClosingElementTags.includes(node.nodeName);
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
const whitespace = `[^\\S\\u00A0\\u0009\\ufeff]`; // for formatting (no "real" content) (TODO: 0009 shouldn't be included)
const whitespaceRegex = new RegExp(`^${whitespace}*$`);
export function isWhitespace(value) {
    const str = typeof value === 'string' ? value : value.nodeValue;
    return whitespaceRegex.test(str);
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
    return !!node && (
        (node.nodeType === Node.TEXT_NODE && isVisibleTextNode(node)) ||
        (node.nodeType === Node.ELEMENT_NODE &&
            (node.getAttribute("t-esc") || node.getAttribute("t-out"))) ||
        isSelfClosingElement(node) ||
        isIconElement(node) ||
        hasVisibleContent(node)
    );
}
export function hasVisibleContent(node) {
    return [...(node?.childNodes || [])].some(n => isVisible(n));
}
const visibleCharRegex = /[^\s\u200b]|[\u00A0\u0009]$/; // contains at least a char that is always visible (TODO: 0009 shouldn't be included)
export function isVisibleTextNode(testedNode) {
    if (!testedNode || !testedNode.length || testedNode.nodeType !== Node.TEXT_NODE) {
        return false;
    }
    if (visibleCharRegex.test(testedNode.textContent) || (isInPre(testedNode) && isWhitespace(testedNode))) {
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
    if (!["UL", "OL"].includes(pnode.tagName)) return;
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

export function toggleList(node, mode, offset = 0) {
    let pnode = node.closest('ul, ol');
    if (!pnode) return;
    const listMode = getListMode(pnode) + mode;
    if (['OLCL', 'ULCL'].includes(listMode)) {
        pnode.classList.add('o_checklist');
        for (let li = pnode.firstElementChild; li !== null; li = li.nextElementSibling) {
            if (li.style.listStyle !== 'none') {
                li.style.listStyle = null;
                if (!li.style.all) li.removeAttribute('style');
            }
        }
        pnode = setTagName(pnode, 'UL');
    } else if (['CLOL', 'CLUL'].includes(listMode)) {
        toggleClass(pnode, 'o_checklist');
        pnode = setTagName(pnode, mode);
    } else if (['OLUL', 'ULOL'].includes(listMode)) {
        pnode = setTagName(pnode, mode);
    } else {
        // toggle => remove list
        let currNode = node;
        while (currNode) {
            currNode = currNode.oShiftTab(offset);
        }
        return;
    }
    return pnode;
}

/**
 * Converts a list element and its nested elements to the specified list mode.
 *
 * @param {HTMLUListElement|HTMLOListElement|HTMLLIElement} node - HTML element
 * representing a list or list item.
 * @param {string} toMode - Target list mode
 * @returns {HTMLUListElement|HTMLOListElement|HTMLLIElement} node - Modified
 * list element after conversion.
 */
export function convertList(node, toMode) {
    if (!["UL", "OL", "LI"].includes(node.nodeName)) return;
    const listMode = getListMode(node);
    if (listMode && toMode !== listMode) {
        node = toggleList(node, toMode);
    }
    for (const child of node.childNodes) {
        convertList(child, toMode);
    }

    return node;
}

export function toggleClass(node, className) {
    node.classList.toggle(className);
    if (!node.className) {
        node.removeAttribute('class');
    }
}

export function makeZeroWidthCharactersVisible(text) {
    return text.replaceAll('\u200B', '//ZWSP//').replaceAll('\uFEFF', '//ZWNBSP//');
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
    return !(getState(...rightPos(brEl), DIRECTIONS.RIGHT).cType & (CTYPES.CONTENT | CTGROUPS.BR));
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
    if (isIconElement(blockEl) || visibleCharRegex.test(blockEl.textContent)) {
        return false;
    }
    if (blockEl.querySelectorAll('br').length >= 2) {
        return false;
    }
    const nodes = blockEl.querySelectorAll('*');
    for (const node of nodes) {
        // There is no text and no double BR, the only thing that could make
        // this visible is a "visible empty" node like an image.
        if (node.nodeName != 'BR' && (isSelfClosingElement(node) || isIconElement(node))) {
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

/**
 * Finds the font size to display for the current selection. We cannot rely
 * on the computed font-size only as font-sizes are responsive and we always
 * want to display the desktop (integer when possible) one.
 *
 * @private
 * @todo probably move `getCSSVariableValue` and `convertNumericToUnit` as
 *       odoo-editor utils.
 * @param {Selection} sel The current selection.
 * @returns {Float} The font size to display.
 */
export function getFontSizeDisplayValue(sel, getCSSVariableValue, convertNumericToUnit) {
    const tagNameRelatedToFontSize = ["h1", "h2", "h3", "h4", "h5", "h6"];
    const styleClassesRelatedToFontSize = ["display-1", "display-2", "display-3", "display-4", "lead"];
    const closestStartContainerEl = closestElement(sel.getRangeAt(0).startContainer);
    const closestFontSizedEl = closestStartContainerEl.closest(`
        [style*='font-size'],
        ${FONT_SIZE_CLASSES.map(className => `.${className}`)},
        ${styleClassesRelatedToFontSize.map(className => `.${className}`)},
        ${tagNameRelatedToFontSize}
    `);
    let remValue;
    if (closestFontSizedEl) {
        const useFontSizeInput = closestFontSizedEl.style.fontSize;
        if (useFontSizeInput) {
            // Use the computed value to always convert to px. However, this
            // currently does not check that the inline font-size is the one
            // actually having an effect (there could be an !important CSS rule
            // forcing something else).
            // TODO align with the behavior of the rest of the editor snippet
            // options.
            return parseFloat(getComputedStyle(closestStartContainerEl).fontSize);
        }
        // It's a class font size or a hN tag. We don't return the computed
        // font size because it can be different from the one displayed in
        // the toolbar because it's responsive.
        const fontSizeClass = FONT_SIZE_CLASSES.find(
            className => closestFontSizedEl.classList.contains(className));
        let fsName;
        if (fontSizeClass) {
            fsName = fontSizeClass.substring(0, fontSizeClass.length - 3); // Without -fs
        } else {
            fsName = styleClassesRelatedToFontSize.find(
                    className => closestFontSizedEl.classList.contains(className))
                || closestFontSizedEl.tagName.toLowerCase();
        }
        remValue = parseFloat(getCSSVariableValue(`${fsName}-font-size`));
    }
    const pxValue = remValue && convertNumericToUnit(remValue, "rem", "px");
    return pxValue || parseFloat(getComputedStyle(closestStartContainerEl).fontSize);
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
 * @param {Node} textNode
 * @param {number} offset
 * @param {DIRECTIONS} originalNodeSide Whether the original node ends up on left
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
    // e.g.: <p>Test/banner</p> + ENTER <=> <p>Test</p><div class="o_editor_banner>...</div><p><br></p>
    const blockEl = closestBlock(after);
    if (blockEl) {
        fillEmpty(blockEl);
    }
    element.before(before);
    element.after(after);
    element.remove();
    return [before, after];
}

/**
 * Split around the given elements, until a given ancestor (included). Elements
 * will be removed in the process so caution is advised in dealing with their
 * references. Returns the new split root element that is a clone of
 * limitAncestor or the original limitAncestor if no split occured.
 *
 * @see splitElement
 * @param {Node[] | Node} elements
 * @param {Node} limitAncestor
 * @returns {[Node, Node]}
 */
export function splitAroundUntil(elements, limitAncestor) {
    elements = Array.isArray(elements) ? elements : [elements];
    const firstNode = elements[0];
    const lastNode = elements[elements.length - 1];
    if ([firstNode, lastNode].includes(limitAncestor)) {
        return limitAncestor;
    }
    let before = firstNode.previousSibling;
    let after = lastNode.nextSibling;
    let beforeSplit, afterSplit;
    if (!before && !after && elements[0] !== limitAncestor) {
        return splitAroundUntil(elements[0].parentElement, limitAncestor);
    }
    // Split up ancestors up to font
    while (after && after.parentElement !== limitAncestor) {
        afterSplit = splitElement(after.parentElement, childNodeIndex(after))[0];
        after = afterSplit.nextSibling;
    }
    if (after) {
        afterSplit = splitElement(limitAncestor, childNodeIndex(after))[0];
        limitAncestor = afterSplit;
    }
    while (before && before.parentElement !== limitAncestor) {
        beforeSplit = splitElement(before.parentElement, childNodeIndex(before) + 1)[1];
        before = beforeSplit.previousSibling;
    }
    if (before) {
        beforeSplit = splitElement(limitAncestor, childNodeIndex(before) + 1)[1];
    }
    return beforeSplit || afterSplit || limitAncestor;
}

export function insertText(sel, content) {
    if (!content) {
        return;
    }
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
 * Inserts the given characters at the given offset of the given node.
 *
 * @param {string} chars
 * @param {Node} node
 * @param {number} offset
 */
export function insertCharsAt(chars, node, offset) {
    if (node.nodeType === Node.TEXT_NODE) {
        const startValue = node.nodeValue;
        if (offset < 0 || offset > startValue.length) {
            throw new Error(`Invalid ${chars} insertion in text node`);
        }
        node.nodeValue = startValue.slice(0, offset) + chars + startValue.slice(offset);
    } else {
        if (offset < 0 || offset > node.childNodes.length) {
            throw new Error(`Invalid ${chars} insertion in non-text node`);
        }
        const textNode = document.createTextNode(chars);
        if (offset < node.childNodes.length) {
            node.insertBefore(textNode, node.childNodes[offset]);
        } else {
            node.appendChild(textNode);
        }
    }
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
    if (!isTangible(el) && !el.hasAttribute("data-oe-zws-empty-inline") && !el.hasChildNodes()) {
        // As soon as there is actual content in the node, the zero-width space
        // is removed by the sanitize function.
        const zws = document.createTextNode('\u200B');
        el.appendChild(zws);
        el.setAttribute("data-oe-zws-empty-inline", "");
        fillers.zws = zws;
        const previousSibling = el.previousSibling;
        if (previousSibling && previousSibling.nodeName === "BR") {
            previousSibling.remove();
        }
        setSelection(zws, 0, zws, 0);
    }
    // If the element is empty and inside an <a> tag with 'inline' display,
    // it's not possible to place the cursor in element even if it contains
    // ZWSP. To make the element cursor-friendly, change its display to
    // 'inline-block'.
    if (
        !isVisible(el) &&
        el.nodeName !== 'A' &&
        closestElement(el, 'a') &&
        getComputedStyle(el).display === 'inline'
    ) {
        el.style.display = 'inline-block';
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

export function setTagName(el, newTagName) {
    if (el.tagName === newTagName) {
        return el;
    }
    const n = document.createElement(newTagName);
    if (el.nodeName !== 'LI') {
        el.style.removeProperty('list-style');
        const attributes = el.attributes;
        for (const attr of attributes) {
            n.setAttribute(attr.name, attr.value);
        }
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
/**
 * Remove ouid of a node and it's descendants in order to allow that tree
 * to be moved into another parent.
 */
export function resetOuids(node) {
    node.ouid = undefined;
    for (const descendant of descendants(node)) {
        descendant.ouid = undefined;
    }
}

//------------------------------------------------------------------------------
// Prepare / Save / Restore state utilities
//------------------------------------------------------------------------------

const prepareUpdateLockedEditables = new Set();
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
 * @param {Object} [options]
 * @param {boolean} [options.allowReenter = true] - if false, all calls to
 *     prepareUpdate before this one gets restored will be ignored.
 * @param {string} [options.label = <random 6 character string>]
 * @param {boolean} [options.debug = false] - if true, adds nicely formatted
 *     console logs to help with debugging.
 * @returns {function}
 */
export function prepareUpdate(...args) {
    const closestRoot = args.length && ancestors(args[0]).find(ancestor => ancestor.oid === 'root');
    const isPrepareUpdateLocked = closestRoot && prepareUpdateLockedEditables.has(closestRoot);
    const hash = (Math.random() + 1).toString(36).substring(7);
    const options = {
        allowReenter: true,
        label: hash,
        debug: false,
        ...(args.length && args[args.length - 1] instanceof Object ? args.pop() : {}),
    };
    if (options.debug) {
        console.log(
            '%cPreparing%c update: ' + options.label +
            (options.label === hash ? '' : ` (${hash})`) +
            '%c' + (isPrepareUpdateLocked ? ' LOCKED' : ''),
            'color: cyan;',
            'color: white;',
            'color: red; font-weight: bold;',
        );
    }
    if (isPrepareUpdateLocked) {
        return () => {
            if (options.debug) {
                console.log(
                    '%cRestoring%c update: ' + options.label +
                    (options.label === hash ? '' : ` (${hash})`) +
                    '%c LOCKED',
                    'color: lightgreen;',
                    'color: white;',
                    'color: red; font-weight: bold;',
                );
            }
        };
    }
    if (!options.allowReenter && closestRoot) {
        prepareUpdateLockedEditables.add(closestRoot);
    }
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
        const right = getState(el, offset, DIRECTIONS.RIGHT, left.cType);
        if (options.debug) {
            const editable = el && closestElement(el, '.odoo-editor-editable');
            const oldEditableHTML = editable && makeZeroWidthCharactersVisible(editable.innerHTML).replaceAll(' ', '_') || '';
            left.oldEditableHTML = oldEditableHTML;
            right.oldEditableHTML = oldEditableHTML;
        }
        restoreData.push(left, right);
    }

    // Create the callback that will be able to restore the state in each
    // direction wherever the node in the opposite direction has landed.
    return function restoreStates() {
        if (options.debug) {
            console.log(
                '%cRestoring%c update: ' + options.label +
                (options.label === hash ? '' : ` (${hash})`),
                'color: lightgreen;',
                'color: white;',
            );
        }
        for (const data of restoreData) {
            restoreState(data, options.debug);
        }
        if (!options.allowReenter && closestRoot) {
            prepareUpdateLockedEditables.delete(closestRoot);
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
 * @param {DIRECTIONS} direction @see DIRECTIONS.LEFT @see DIRECTIONS.RIGHT
 * @param {CTYPES} [leftCType]
 * @returns {Object}
 */
export function getState(el, offset, direction, leftCType) {
    const leftDOMPath = leftLeafOnlyNotBlockPath;
    const rightDOMPath = rightLeafOnlyNotBlockPath;

    let domPath;
    let inverseDOMPath;
    const whitespaceAtStartRegex = new RegExp('^' + whitespace + '+');
    const whitespaceAtEndRegex = new RegExp(whitespace + '+$');
    const reasons = [];
    if (direction === DIRECTIONS.LEFT) {
        domPath = leftDOMPath(el, offset, reasons);
        inverseDOMPath = rightDOMPath(el, offset);
    } else {
        domPath = rightDOMPath(el, offset, reasons);
        inverseDOMPath = leftDOMPath(el, offset);
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
            // ZWNBSP are technical characters which should be ignored.
            const value = node.nodeValue.replaceAll('\ufeff', '');
            // If we hit a text node, the state depends on the path direction:
            // any space encountered backwards is a visible space if we hit
            // visible content afterwards. If going forward, spaces are only
            // visible if we have content backwards.
            if (direction === DIRECTIONS.LEFT) {
                if (!isWhitespace(value)) {
                    if (lastSpace) {
                        cType = CTYPES.SPACE;
                    } else {
                        const rightLeaf = rightLeafOnlyNotBlockPath(node).next().value;
                        const hasContentRight = rightLeaf && !whitespaceAtStartRegex.test(rightLeaf.textContent);
                        cType = !hasContentRight && whitespaceAtEndRegex.test(node.textContent) ? CTYPES.SPACE : CTYPES.CONTENT;
                    }
                    break;
                }
                if (value.length) {
                    lastSpace = node;
                }
            } else {
                leftCType = leftCType || getState(el, offset, DIRECTIONS.LEFT).cType;
                if (whitespaceAtStartRegex.test(value)) {
                    const leftLeaf = leftLeafOnlyNotBlockPath(node).next().value;
                    const hasContentLeft = leftLeaf && !whitespaceAtEndRegex.test(leftLeaf.textContent);
                    const rct = !isWhitespace(value)
                        ? CTYPES.CONTENT
                        : getState(...rightPos(node), DIRECTIONS.RIGHT).cType;
                    cType =
                        leftCType & CTYPES.CONTENT && rct & (CTYPES.CONTENT | CTYPES.BR) && !hasContentLeft
                            ? CTYPES.SPACE
                            : rct;
                    break;
                }
                if (!isWhitespace(value)) {
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
        // Replace a space by &nbsp; when it was content before and now it is
        // a BR (removal of last character before a BR for example).
        { direction: DIRECTIONS.RIGHT, cType1: CTGROUPS.CONTENT, cType2: CTGROUPS.BR },
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
 * @param {boolean} debug=false - if true, adds nicely formatted
 *     console logs to help with debugging.
 * @returns {Object|undefined} the rule that was applied to restore the state,
 *     if any, for testing purposes.
 */
export function restoreState(prevStateData, debug=false) {
    const { node, direction, cType: cType1, oldEditableHTML } = prevStateData;
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
    if (debug) {
        const editable = closestElement(node, '.odoo-editor-editable');
        console.log(
            '%c' + makeZeroWidthCharactersVisible(node.textContent).replaceAll(' ', '_') + '\n' +
            '%c' + (direction === DIRECTIONS.LEFT ? 'left' : 'right') + '\n' +
            '%c' + ctypeToString(cType1) + '\n' +
            '%c' + ctypeToString(cType2) + '\n' +
            '%c' + 'BEFORE: ' + (oldEditableHTML || '(unavailable)') + '\n' +
            '%c' + 'AFTER:  ' + (editable ? makeZeroWidthCharactersVisible(editable.innerHTML).replaceAll(' ', '_') : '(unavailable)') + '\n',
            'color: white; display: block; width: 100%;',
            'color: ' + (direction === DIRECTIONS.LEFT ? 'magenta' : 'lightgreen') + '; display: block; width: 100%;',
            'color: pink; display: block; width: 100%;',
            'color: lightblue; display: block; width: 100%;',
            'color: white; display: block; width: 100%;',
            'color: white; display: block; width: 100%;',
            rule,
        );
    }
    if (Object.values(rule).filter(x => x !== undefined).length) {
        const inverseDirection = direction === DIRECTIONS.LEFT ? DIRECTIONS.RIGHT : DIRECTIONS.LEFT;
        enforceWhitespace(el, offset, inverseDirection, rule);
    }
    return rule;
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
    let domPath, whitespaceAtEdgeRegex;
    if (direction === DIRECTIONS.LEFT) {
        domPath = leftLeafOnlyNotBlockPath(el, offset);
        whitespaceAtEdgeRegex = new RegExp(whitespace + '+$');
    } else {
        domPath = rightLeafOnlyNotBlockPath(el, offset);
        whitespaceAtEdgeRegex = new RegExp('^' + whitespace + '+');
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
            if (whitespaceAtEdgeRegex.test(node.nodeValue)) {
                // If we hit spaces going in the direction, either they are in a
                // visible text node and we have to change the visibility of
                // those spaces, or it is in an invisible text node. In that
                // last case, we either remove the spaces if there are spaces in
                // a visible text node going further in the direction or we
                // change the visiblity or those spaces.
                if (!isWhitespace(node)) {
                    foundVisibleSpaceTextNode = node;
                    break;
                } else {
                    invisibleSpaceTextNodes.push(node);
                }
            } else if (!isWhitespace(node)) {
                break;
            }
        } else {
            break;
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
            getState(...rightPos(spaceNode), DIRECTIONS.RIGHT).cType & CTGROUPS.BLOCK &&
            getState(...leftPos(spaceNode), DIRECTIONS.LEFT).cType !== CTYPES.CONTENT
        ) {
            spaceVisibility = false;
        }
        spaceNode.nodeValue = spaceNode.nodeValue.replace(whitespaceAtEdgeRegex, spaceVisibility ? '\u00A0' : '');
    }
}

/**
 * Takes a color (rgb, rgba or hex) and returns its hex representation. If the
 * color is given in rgba, the background color of the node whose color we're
 * converting is used in conjunction with the alpha to compute the resulting
 * color (using the formula: `alpha*color + (1 - alpha)*background` for each
 * channel).
 *
 * @param {string} rgb
 * @param {HTMLElement} [node]
 * @returns {string} hexadecimal color (#RRGGBB)
 */
export function rgbToHex(rgb = '', node = null) {
    if (rgb.startsWith('#')) {
        return rgb;
    } else if (rgb.startsWith('rgba')) {
        const values = rgb.match(/[\d\.]{1,5}/g) || [];
        const alpha = parseFloat(values.pop());
        // Retrieve the background color.
        let bgRgbValues = [];
        if (node) {
            let bgColor = getComputedStyle(node).backgroundColor;
            if (bgColor.startsWith('rgba')) {
                // The background color is itself rgba so we need to compute
                // the resulting color using the background color of its
                // parent.
                bgColor = rgbToHex(bgColor, node.parentElement);
            }
            if (bgColor && bgColor.startsWith('#')) {
                bgRgbValues = (bgColor.match(/[\da-f]{2}/gi) || []).map(val => parseInt(val, 16));
            } else if (bgColor && bgColor.startsWith('rgb')) {
                bgRgbValues = (bgColor.match(/[\d\.]{1,5}/g) || []).map(val => parseInt(val));
            }
        }
        bgRgbValues = bgRgbValues.length ? bgRgbValues : [255, 255, 255]; // Default to white.

        return (
            '#' +
            values.map((value, index) => {
                const converted = Math.floor(alpha * parseInt(value) + (1 - alpha) * bgRgbValues[index]);
                const hex = parseInt(converted).toString(16);
                return hex.length === 1 ? '0' + hex : hex;
            }).join('')
        );
    } else {
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
}

export function parseHTML(document, html) {
    const fragment = document.createDocumentFragment();
    const parser = new document.defaultView.DOMParser();
    const parsedDocument = parser.parseFromString(html, 'text/html');
    fragment.replaceChildren(...parsedDocument.body.childNodes);
    return fragment;
}

/**
 * Take a string containing a size in pixels, return that size as a float.
 *
 * @param {string} sizeString
 * @returns {number}
 */
export function pxToFloat(sizeString) {
    return parseFloat(sizeString.replace('px', ''));
}

/**
 * Returns position of a range in form of object (end
 * position of a range in case of non-collapsed range).
 *
 * @param {HTMLElement} el element for which range postion will be calculated
 * @param {Document} document
 * @param {Object} [options]
 * @param {Number} [options.marginRight] right margin to be considered
 * @param {Number} [options.marginBottom] bottom margin to be considered
 * @param {Number} [options.marginTop] top margin to be considered
 * @param {Number} [options.marginLeft] left margin to be considered
 * @param {Function} [options.getContextFromParentRect] to get context rect from parent
 * @returns {Object | undefined}
 */
export function getRangePosition(el, document, options = {}) {
    const selection = document.getSelection();
    if (!selection.rangeCount) return;
    const range = selection.getRangeAt(0);
    const isRtl = options.direction === 'rtl';

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

    if (!offset || offset.height === 0) {
        const clonedRange = range.cloneRange();
        const shadowCaret = document.createTextNode('|');
        clonedRange.insertNode(shadowCaret);
        clonedRange.selectNode(shadowCaret);
        const rect = clonedRange.getBoundingClientRect();
        offset = { height: rect.height, left: rect.left, top: rect.top };
        shadowCaret.remove();
        clonedRange.detach();
    }

    if (isRtl) {
        // To handle the RTL case we shift the elelement to the left by its size
        // and handle it the same as left.
        offset.right = offset.left - el.offsetWidth;
        const leftMove = Math.max(0, offset.right + el.offsetWidth + marginLeft - window.innerWidth);
        if (leftMove && offset.right - leftMove > marginRight) {
            offset.right -= leftMove;
        } else if (offset.right - leftMove < marginRight) {
            offset.right = marginRight;
        }
    }

    const leftMove = Math.max(0, offset.left + el.offsetWidth + marginRight - window.innerWidth);
    if (leftMove && offset.left - leftMove > marginLeft) {
        offset.left -= leftMove;
    } else if (offset.left - leftMove < marginLeft) {
        offset.left = marginLeft;
    }

    if (options.getContextFromParentRect) {
        const parentContextRect = options.getContextFromParentRect();
        offset.left += parentContextRect.left;
        offset.top += parentContextRect.top;
        if (isRtl) {
            offset.right += parentContextRect.left;
        }
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
        if (isRtl) {
            offset.right += window.scrollX;
        }
    }
    if (isRtl) {
        // Get the actual right value.
        offset.right = window.innerWidth - offset.right - el.offsetWidth;
    }

    return offset;
}

export const isNotEditableNode = node =>
    node.getAttribute &&
    node.getAttribute('contenteditable') &&
    node.getAttribute('contenteditable').toLowerCase() === 'false';

export const isRoot = node => node.oid === "root";

export const leftLeafFirstPath = createDOMPathGenerator(DIRECTIONS.LEFT);
export const leftLeafOnlyNotBlockPath = createDOMPathGenerator(DIRECTIONS.LEFT, {
    leafOnly: true,
    stopTraverseFunction: isBlock,
    stopFunction: node => isBlock(node) || isRoot(node),
});
export const leftLeafOnlyInScopeNotBlockEditablePath = createDOMPathGenerator(DIRECTIONS.LEFT, {
    leafOnly: true,
    inScope: true,
    stopTraverseFunction: node => isNotEditableNode(node) || isBlock(node),
    stopFunction: node => isNotEditableNode(node) || isBlock(node) || isRoot(node),
});

export const rightLeafOnlyNotBlockPath = createDOMPathGenerator(DIRECTIONS.RIGHT, {
    leafOnly: true,
    stopTraverseFunction: isBlock,
    stopFunction: node => isBlock(node) || isRoot(node),
});

export const rightLeafOnlyPathNotBlockNotEditablePath = createDOMPathGenerator(DIRECTIONS.RIGHT, {
    leafOnly: true,
    stopFunction: node => isRoot(node),
});
export const rightLeafOnlyInScopeNotBlockEditablePath = createDOMPathGenerator(DIRECTIONS.RIGHT, {
    leafOnly: true,
    inScope: true,
    stopTraverseFunction: node => isNotEditableNode(node) || isBlock(node),
    stopFunction: node => isNotEditableNode(node) || isBlock(node) || isRoot(node),
});
export const rightLeafOnlyNotBlockNotEditablePath = createDOMPathGenerator(DIRECTIONS.RIGHT, {
    leafOnly: true,
    stopTraverseFunction: node => isNotEditableNode(node) || isBlock(node),
    stopFunction: node => isBlock(node) && !isNotEditableNode(node) || isRoot(node),
});
//------------------------------------------------------------------------------
// Miscelaneous
//------------------------------------------------------------------------------
export function peek(arr) {
    return arr[arr.length - 1];
}
/**
 * Check user OS
 * @returns {boolean}
 */
export function isMacOS() {
    return window.navigator.userAgent.includes('Mac');
}

/**
 * Remove zero-width spaces from the provided node and its descendants.
 * Note: Does NOT remove zero-width NON-BREAK spaces (feff)!
 *
 * @param {Node} node
 */
export function cleanZWS(node) {
    [node, ...descendants(node)]
        .filter(node => node.nodeType === Node.TEXT_NODE && node.nodeValue.includes('\u200B'))
        .forEach(node => node.nodeValue = node.nodeValue.replace(/\u200B/g, ''));
}
