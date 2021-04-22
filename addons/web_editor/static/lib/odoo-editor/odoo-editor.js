odoo.define('web_editor.odoo-editor', (function(require) {
var exportVariable = (function (exports) {
    'use strict';

    const INVISIBLE_REGEX = /\u200c/g;

    const DIRECTIONS = {
        LEFT: false,
        RIGHT: true,
    };
    const CTYPES = {
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
    const CTGROUPS = {
        // Short for CONTENT_TYPE_GROUPS
        INLINE: CTYPES.CONTENT | CTYPES.SPACE,
        BLOCK: CTYPES.BLOCK_OUTSIDE | CTYPES.BLOCK_INSIDE,
        BR: CTYPES.BR,
    };

    //------------------------------------------------------------------------------
    // Position and sizes
    //------------------------------------------------------------------------------

    /**
     * @param {Node} node
     * @returns {Array.<HTMLElement, number>}
     */
    function leftPos(node) {
        return [node.parentNode, childNodeIndex(node)];
    }
    /**
     * @param {Node} node
     * @returns {Array.<HTMLElement, number>}
     */
    function rightPos(node) {
        return [node.parentNode, childNodeIndex(node) + 1];
    }
    /**
     * @param {Node} node
     * @returns {Array.<HTMLElement, number, HTMLElement, number>}
     */
    function boundariesOut(node) {
        const index = childNodeIndex(node);
        return [node.parentNode, index, node.parentNode, index + 1];
    }
    /**
     * @param {Node} node
     * @returns {Array.<Node, number>}
     */
    function startPos(node) {
        return [node, 0];
    }
    /**
     * @param {Node} node
     * @returns {Array.<Node, number>}
     */
    function endPos(node) {
        return [node, nodeSize(node)];
    }
    /**
     * @param {Node} node
     * @returns {Array.<node, number, node, number>}
     */
    function boundariesIn(node) {
        return [node, 0, node, nodeSize(node)];
    }
    /**
     * Returns the given node's position relative to its parent (= its index in the
     * child nodes of its parent).
     *
     * @param {Node} node
     * @returns {number}
     */
    function childNodeIndex(node) {
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
    function nodeSize(node) {
        const isTextNode = node.nodeType === Node.TEXT_NODE;
        return isTextNode ? node.length : node.childNodes.length;
    }

    //------------------------------------------------------------------------------
    // DOM Path and node search functions
    //------------------------------------------------------------------------------

    const closestPath = function* (node) {
        while (node) {
            yield node;
            node = node.parentNode;
        }
    };

    const leftDeepFirstPath = createDOMPathGenerator(DIRECTIONS.LEFT, false, false);
    const leftDeepOnlyPath = createDOMPathGenerator(DIRECTIONS.LEFT, true, false);
    const leftDeepFirstInlinePath = createDOMPathGenerator(DIRECTIONS.LEFT, false, true);
    const leftDeepOnlyInlinePath = createDOMPathGenerator(DIRECTIONS.LEFT, true, true);
    const leftDeepOnlyInlineInScopePath = createDOMPathGenerator(
        DIRECTIONS.LEFT,
        true,
        true,
        true,
    );

    const rightDeepFirstPath = createDOMPathGenerator(DIRECTIONS.RIGHT, false, false);
    const rightDeepOnlyPath = createDOMPathGenerator(DIRECTIONS.RIGHT, true, false);
    const rightDeepFirstInlinePath = createDOMPathGenerator(DIRECTIONS.RIGHT, false, true);
    const rightDeepOnlyInlinePath = createDOMPathGenerator(DIRECTIONS.RIGHT, true, true);
    const rightDeepOnlyInlineInScopePath = createDOMPathGenerator(
        DIRECTIONS.RIGHT,
        true,
        true,
        true,
    );
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
     * @see leftDeepFirstPath
     * @see leftDeepOnlyPath
     * @see leftDeepFirstInlinePath
     * @see leftDeepOnlyInlinePath
     *
     * @see rightDeepFirstPath
     * @see rightDeepOnlyPath
     * @see rightDeepFirstInlinePath
     * @see rightDeepOnlyInlinePath
     *
     * @param {number} direction
     * @param {boolean} deepOnly
     * @param {boolean} inline
     */
    function createDOMPathGenerator(direction, deepOnly, inline, inScope = false) {
        const nextDeepest =
            direction === DIRECTIONS.LEFT
                ? node => lastLeaf(node.previousSibling, inline)
                : node => firstLeaf(node.nextSibling, inline);

        const firstNode =
            direction === DIRECTIONS.LEFT
                ? (node, offset) => lastLeaf(node.childNodes[offset - 1], inline)
                : (node, offset) => firstLeaf(node.childNodes[offset], inline);

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
                if (inline && isBlock(currentNode)) {
                    reasons.push(movedUp ? PATH_END_REASONS.BLOCK_OUT : PATH_END_REASONS.BLOCK_HIT);
                    break;
                }
                if (inScope && currentNode === node) {
                    reasons.push(PATH_END_REASONS.OUT_OF_SCOPE);
                    break;
                }
                if (!deepOnly || !movedUp) {
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
    function findNode(domPath, findCallback = () => true, stopCallback = () => false) {
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
     * @returns {HTMLElement}
     */
    function closestElement(node, selector) {
        const element = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
        return selector && element ? element.closest(selector) : element || node;
    }

    /**
     * Returns a list of all the ancestors nodes of the provided node.
     *
     * @param {Node} node
     * @returns {HTMLElement[]}
     */
    function ancestors(node, editable) {
        if (!node || !node.parentElement || node === editable) return [];
        return [node.parentElement, ...ancestors(node.parentElement, editable)];
    }

    function closestBlock(node) {
        return findNode(closestPath(node), node => isBlock(node));
    }
    /**
     * Returns the deepest child in last position.
     *
     * @param {Node} node
     * @param {boolean} [stopAtBlock=false]
     * @returns {Node}
     */
    function lastLeaf(node, stopAtBlock = false) {
        while (node && node.lastChild && !(stopAtBlock && isBlock(node))) {
            node = node.lastChild;
        }
        return node;
    }
    /**
     * Returns the deepest child in first position.
     *
     * @param {Node} node
     * @param {boolean} [stopAtBlock=false]
     * @returns {Node}
     */
    function firstLeaf(node, stopAtBlock = false) {
        while (node && node.firstChild && !(stopAtBlock && isBlock(node))) {
            node = node.firstChild;
        }
        return node;
    }
    function previousLeaf(node, editable, skipInvisible = false) {
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
    function nextLeaf(node, editable, skipInvisible = false) {
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
    function getAdjacentPreviousSiblings(node, predicate = n => !!n) {
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
    function getAdjacentNextSiblings(node, predicate = n => !!n) {
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
    function getAdjacents(node, predicate = n => !!n) {
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
    function getNormalizedCursorPosition(node, offset, full = true) {
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
                const leftInlineNode = leftDeepOnlyInlineInScopePath(el, elOffset).next().value;
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
                    const rightInlineNode = rightDeepOnlyInlineInScopePath(el, elOffset).next().value;
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
    function setCursor(
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
    function setCursorStart(node, normalize = true) {
        const pos = startPos(node);
        return setCursor(...pos, ...pos, normalize);
    }
    /**
     * @param {Node} node
     * @param {boolean} [normalize=true]
     * @returns {?Array.<Node, number}
     */
    function setCursorEnd(node, normalize = true) {
        const pos = endPos(node);
        return setCursor(...pos, ...pos, normalize);
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
    function getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset) {
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
    function getTraversedNodes(editable) {
        const document = editable.ownerDocument;
        const range = getDeepRange(editable);
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
    function getSelectedNodes(editable) {
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
    function getDeepRange(editable, { range, sel, splitText, select, correctTripleClick } = {}) {
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
        if (correctTripleClick && !endOffset && !end.previousSibling) {
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

    function getDeepestPosition(node, offset) {
        let found = false;
        while (node.hasChildNodes()) {
            let newNode = node.childNodes[offset];
            if (newNode) {
                newNode = getNextVisibleNode(newNode);
                if (!newNode || isEmptyBlock(newNode)) break;
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
                if (!newNode || isEmptyBlock(newNode)) break;
                node = newNode;
                offset = nodeSize(node);
            }
        }
        let didMove = false;
        let reversed = false;
        while (!isVisible(node) && (node.previousSibling || (!reversed && node.nextSibling))) {
            reversed = reversed || !node.nextSibling;
            node = reversed ? node.previousSibling : node.nextSibling;
            offset = 0;
            didMove = true;
        }
        return didMove && isVisible(node) ? getDeepestPosition(node, offset) : [node, offset];
    }

    function getCursors(document) {
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

    function preserveCursor(document) {
        const sel = document.getSelection();
        const cursorPos = [sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset];
        return replace => {
            replace = replace || new Map();
            cursorPos[0] = replace.get(cursorPos[0]) || cursorPos[0];
            cursorPos[2] = replace.get(cursorPos[2]) || cursorPos[2];
            setCursor(...cursorPos);
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
     * */
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
    function isBlock(node) {
        if (!(node instanceof Element)) {
            return false;
        }
        const tagName = node.nodeName.toUpperCase();
        // Every custom jw-* node will be considered as blocks.
        if (tagName.startsWith('JW-') || tagName === 'T') {
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

    function isUnbreakable(node) {
        if (!node || node.nodeType === Node.TEXT_NODE || !node.isContentEditable) {
            return false;
        }
        if (node.nodeType !== Node.ELEMENT_NODE) {
            return true;
        }
        return (
            isUnremovable(node) || // An unremovable node is always unbreakable.
            ['THEAD', 'TBODY', 'TFOOT', 'TR', 'TH', 'TD', 'SECTION', 'DIV'].includes(node.tagName) ||
            node.hasAttribute('t') ||
            node.classList.contains('oe_unbreakable')
        );
    }

    function isUnremovable(node) {
        if (node.nodeType !== Node.ELEMENT_NODE && node.nodeType !== Node.TEXT_NODE) {
            return true;
        }
        const isEditableRoot =
            node.isContentEditable &&
            node.parentElement &&
            !node.parentElement.isContentEditable &&
            node.nodeName !== 'A'; // links can be their own contenteditable but should be removable by default.
        return isEditableRoot || (node.classList && node.classList.contains('oe_unremovable'));
    }

    function containsUnbreakable(node) {
        if (!node) {
            return false;
        }
        return isUnbreakable(node) || containsUnbreakable(node.firstChild);
    }
    function isFontAwesome(node) {
        return (
            node &&
            (node.nodeName === 'I' || node.nodeName === 'SPAN') &&
            ['fa', 'fab', 'fad', 'far'].some(faClass => node.classList.contains(faClass))
        );
    }
    function isMediaElement(node) {
        return (
            isFontAwesome(node) ||
            (node.classList &&
                (node.classList.contains('o_image') || node.classList.contains('media_iframe_video')))
        );
    }

    function containsUnremovable(node) {
        if (!node) {
            return false;
        }
        return isUnremovable(node) || containsUnremovable(node.firstChild);
    }

    function getInSelection(document, selector) {
        const selection = document.getSelection();
        const range = !!selection.rangeCount && selection.getRangeAt(0);
        return (
            range &&
            (closestElement(range.startContainer, selector) ||
                [
                    ...closestElement(range.commonAncestorContainer).querySelectorAll(selector),
                ].find(node => range.intersectsNode(node)))
        );
    }

    // optimize: use the parent Oid to speed up detection
    function getOuid(node, optimize = false) {
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
    function isVisibleEmpty(node) {
        return selfClosingElementTags.includes(node.nodeName);
    }
    /**
     * Returns true if the given node is in a PRE context for whitespace handling.
     *
     * @param {Node} node
     * @returns {boolean}
     */
    function isInPre(node) {
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
    function isVisibleStr(value) {
        const str = typeof value === 'string' ? value : value.nodeValue;
        return nonWhitespacesRegex.test(str);
    }
    /**
     * @param {Node} node
     * @returns {boolean}
     */
    function isContentTextNode(node) {
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
     * @returns {boolean}
     */
    function isVisible(node, areBlocksAlwaysVisible = true) {
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

    function parentsGet(node, root = undefined) {
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

    function commonParentGet(node1, node2, root = undefined) {
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

    function getListMode(pnode) {
        if (pnode.tagName == 'OL') return 'OL';
        return pnode.classList.contains('o_checklist') ? 'CL' : 'UL';
    }

    function createList(mode) {
        const node = document.createElement(mode == 'OL' ? 'OL' : 'UL');
        if (mode == 'CL') {
            node.classList.add('o_checklist');
        }
        return node;
    }

    function insertListAfter(afterNode, mode, content = []) {
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

    function toggleClass(node, className) {
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
    function isFakeLineBreak(brEl) {
        return !(getState(...rightPos(brEl), DIRECTIONS.RIGHT).cType & (CTGROUPS.INLINE | CTGROUPS.BR));
    }
    /**
     * Checks whether or not the given block has any visible content, except for
     * a placeholder BR.
     *
     * @param {HTMLElement} blockEl
     * @returns {boolean}
     */
    function isEmptyBlock(blockEl) {
        if (blockEl.nodeType !== Node.ELEMENT_NODE) {
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
    function isShrunkBlock(blockEl) {
        return isEmptyBlock(blockEl) && !blockEl.querySelector('br');
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
    function splitTextNode(textNode, offset, originalNodeSide = DIRECTIONS.RIGHT) {
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
    function splitElement(element, offset) {
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

    function insertText(sel, content) {
        if (sel.anchorNode.nodeType == Node.TEXT_NODE) {
            const pos = [sel.anchorNode.parentElement, splitTextNode(sel.anchorNode, sel.anchorOffset)];
            setCursor(...pos, ...pos, false);
        }
        const txt = document.createTextNode(content || '#');
        const restore = prepareUpdate(sel.anchorNode, sel.anchorOffset);
        sel.getRangeAt(0).insertNode(txt);
        restore();
        setCursor(...boundariesOut(txt), false);
    }

    /**
     * Add a BR in the given node if its closest ancestor block has nothing to make
     * it visible.
     *
     * @param {HTMLElement} el
     */
    function fillEmpty(el) {
        const blockEl = closestBlock(el);
        if (isShrunkBlock(blockEl)) {
            blockEl.appendChild(document.createElement('br'));
        }
    }
    /**
     * Removes the given node if invisible and all its invisible ancestors.
     *
     * @param {Node} node
     * @returns {Node} the first visible ancestor of node (or itself)
     */
    function clearEmpty(node) {
        while (!isVisible(node)) {
            const toRemove = node;
            node = node.parentNode;
            toRemove.remove();
        }
        return node;
    }

    function setTagName(el, newTagName) {
        if (el.tagName == newTagName) {
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
    function moveNodes(
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
    function prepareUpdate(...args) {
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
     * @returns {Object}
     */
    function getState(el, offset, direction, leftCType) {
        const leftDOMPath = leftDeepOnlyInlinePath;
        const rightDOMPath = rightDeepOnlyInlinePath;

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
                const value = node.nodeValue.replace(INVISIBLE_REGEX, '');
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
    function restoreState(prevStateData) {
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
    function enforceWhitespace(el, offset, direction, rule) {
        let domPath;
        let expr;
        if (direction === DIRECTIONS.LEFT) {
            domPath = leftDeepOnlyInlinePath(el, offset);
            expr = /[^\S\u00A0]+$/;
        } else {
            domPath = rightDeepOnlyInlinePath(el, offset);
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

    function rgbToHex(rgb = '') {
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

    Text.prototype.oDeleteBackward = function (offset, alreadyMoved = false) {
        const parentNode = this.parentNode;

        if (!offset) {
            // Backspace at the beginning of a text node is not a specific case to
            // handle, let the element implementation handle it.
            HTMLElement.prototype.oDeleteBackward.call(this, offset, alreadyMoved);
            return;
        }

        // First, split around the character where the backspace occurs
        const firstSplitOffset = splitTextNode(this, offset - 1);
        const secondSplitOffset = splitTextNode(parentNode.childNodes[firstSplitOffset], 1);
        const middleNode = parentNode.childNodes[firstSplitOffset];

        // Do remove the character, then restore the state of the surrounding parts.
        const restore = prepareUpdate(parentNode, firstSplitOffset, parentNode, secondSplitOffset);
        const isSpace = !isVisibleStr(middleNode) && !isInPre(middleNode);
        middleNode.remove();
        restore();

        // If the removed element was not visible content, propagate the backspace.
        if (
            isSpace &&
            getState(parentNode, firstSplitOffset, DIRECTIONS.LEFT).cType !== CTYPES.CONTENT
        ) {
            parentNode.oDeleteBackward(firstSplitOffset, alreadyMoved);
            return;
        }

        fillEmpty(parentNode);
        setCursor(parentNode, firstSplitOffset);
    };

    HTMLElement.prototype.oDeleteBackward = function (offset, alreadyMoved = false) {
        let moveDest;
        if (offset) {
            const leftNode = this.childNodes[offset - 1];
            if (isUnremovable(leftNode)) {
                throw UNREMOVABLE_ROLLBACK_CODE;
            }
            if (isUnbreakable(leftNode)) {
                throw UNBREAKABLE_ROLLBACK_CODE;
            }
            if (isMediaElement(leftNode)) {
                leftNode.remove();
                return;
            }
            if (!isBlock(leftNode) || isVisibleEmpty(leftNode)) {
                /**
                 * Backspace just after an inline node, convert to backspace at the
                 * end of that inline node.
                 *
                 * E.g. <p>abc<i>def</i>[]</p> + BACKSPACE
                 * <=>  <p>abc<i>def[]</i></p> + BACKSPACE
                 */
                leftNode.oDeleteBackward(nodeSize(leftNode), alreadyMoved);
                return;
            }

            /**
             * Backspace just after an block node, we have to move any inline
             * content after it, up to the next block. If the cursor is between
             * two blocks, this is a theoretical case: just do nothing.
             *
             * E.g. <p>abc</p>[]de<i>f</i><p>ghi</p> + BACKSPACE
             * <=>  <p>abcde<i>f</i></p><p>ghi</p>
             */
            alreadyMoved = true;
            moveDest = endPos(leftNode);
        } else {
            if (isUnremovable(this)) {
                throw UNREMOVABLE_ROLLBACK_CODE;
            }
            const parentEl = this.parentNode;

            if (!isBlock(this) || isVisibleEmpty(this)) {
                /**
                 * Backspace at the beginning of an inline node, nothing has to be
                 * done: propagate the backspace. If the node was empty, we remove
                 * it before.
                 *
                 * E.g. <p>abc<b></b><i>[]def</i></p> + BACKSPACE
                 * <=>  <p>abc<b>[]</b><i>def</i></p> + BACKSPACE
                 * <=>  <p>abc[]<i>def</i></p> + BACKSPACE
                 */
                const parentOffset = childNodeIndex(this);
                if (!nodeSize(this)) {
                    const visible = isVisible(this);

                    const restore = prepareUpdate(...boundariesOut(this));
                    this.remove();
                    restore();

                    fillEmpty(parentEl);

                    if (visible) {
                        // TODO this handle BR/IMG/etc removals../ to see if we
                        // prefer to have a dedicated handler for every possible
                        // HTML element or if we let this generic code handle it.
                        setCursor(parentEl, parentOffset);
                        return;
                    }
                }
                parentEl.oDeleteBackward(parentOffset, alreadyMoved);
                return;
            }

            /**
             * Backspace at the beginning of a block node, we have to move the
             * inline content at its beginning outside of the element and propagate
             * to the left block if any.
             *
             * E.g. (prev == block)
             *      <p>abc</p><div>[]def<p>ghi</p></div> + BACKSPACE
             * <=>  <p>abc</p>[]def<div><p>ghi</p></div> + BACKSPACE
             *
             * E.g. (prev != block)
             *      abc<div>[]def<p>ghi</p></div> + BACKSPACE
             * <=>  abc[]def<div><p>ghi</p></div>
             */
            moveDest = leftPos(this);
        }

        let node = this.childNodes[offset];
        let firstBlockIndex = offset;
        while (node && !isBlock(node)) {
            node = node.nextSibling;
            firstBlockIndex++;
        }
        let [cursorNode, cursorOffset] = moveNodes(...moveDest, this, offset, firstBlockIndex);
        setCursor(cursorNode, cursorOffset);

        // Propagate if this is still a block on the left of where the nodes were
        // moved.
        if (
            cursorNode.nodeType === Node.TEXT_NODE &&
            (cursorOffset === 0 || cursorOffset === cursorNode.length)
        ) {
            cursorOffset = childNodeIndex(cursorNode) + (cursorOffset === 0 ? 0 : 1);
            cursorNode = cursorNode.parentNode;
        }
        if (cursorNode.nodeType !== Node.TEXT_NODE) {
            const { cType } = getState(cursorNode, cursorOffset, DIRECTIONS.LEFT);
            if (cType & CTGROUPS.BLOCK && (!alreadyMoved || cType === CTYPES.BLOCK_OUTSIDE)) {
                cursorNode.oDeleteBackward(cursorOffset, alreadyMoved);
            }
        }
    };

    HTMLLIElement.prototype.oDeleteBackward = function (offset, alreadyMoved = false) {
        if (offset > 0 || this.previousElementSibling) {
            // If backspace inside li content or if the li is not the first one,
            // it behaves just like in a normal element.
            HTMLElement.prototype.oDeleteBackward.call(this, offset, alreadyMoved);
            return;
        }
        this.oShiftTab(offset);
    };

    HTMLBRElement.prototype.oDeleteBackward = function (offset, alreadyMoved = false) {
        const parentOffset = childNodeIndex(this);
        const rightState = getState(this.parentElement, parentOffset + 1, DIRECTIONS.RIGHT).cType;
        if (rightState & CTYPES.BLOCK_INSIDE) {
            this.parentElement.oDeleteBackward(parentOffset, alreadyMoved);
        } else {
            HTMLElement.prototype.oDeleteBackward.call(this, offset, alreadyMoved);
        }
    };

    Text.prototype.oDeleteForward = function (offset) {
        if (offset < this.length) {
            this.oDeleteBackward(offset + 1);
        } else {
            HTMLElement.prototype.oDeleteForward.call(this.parentNode, childNodeIndex(this) + 1);
        }
    };

    HTMLElement.prototype.oDeleteForward = function (offset) {
        const filterFunc = node => isVisibleEmpty(node) || isContentTextNode(node);

        const firstInlineNode = findNode(rightDeepOnlyInlinePath(this, offset), filterFunc);
        if (isFontAwesome(firstInlineNode && firstInlineNode.parentElement)) {
            firstInlineNode.parentElement.remove();
            return;
        }
        if (
            firstInlineNode &&
            (firstInlineNode.nodeName !== 'BR' ||
                getState(...rightPos(firstInlineNode), DIRECTIONS.RIGHT).cType !== CTYPES.BLOCK_INSIDE)
        ) {
            firstInlineNode.oDeleteBackward(Math.min(1, nodeSize(firstInlineNode)));
            return;
        }
        const firstOutNode = findNode(
            rightDeepOnlyPath(...(firstInlineNode ? rightPos(firstInlineNode) : [this, offset])),
            filterFunc,
        );
        if (firstOutNode) {
            const [node, offset] = leftPos(firstOutNode);
            node.oDeleteBackward(offset);
            return;
        }
    };

    Text.prototype.oEnter = function (offset) {
        this.parentElement.oEnter(splitTextNode(this, offset), true);
    };
    /**
     * The whole logic can pretty much be described by this example:
     *
     *     <p><span><b>[]xt</b>ab</span>cd</p> + ENTER
     * <=> <p><span><b><br></b>[]<b>xt</b>ab</span>cd</p> + ENTER
     * <=> <p><span><b><br></b></span>[]<span><b>xt</b>ab</span>cd</p> + ENTER
     * <=> <p><span><b><br></b></span></p><p><span><b>[]xt</b>ab</span>cd</p> + SANITIZE
     * <=> <p><br></p><p><span><b>[]xt</b>ab</span>cd</p>
     *
     * Propagate the split for as long as we split an inline node, then refocus the
     * beginning of the first split node
     */
    HTMLElement.prototype.oEnter = function (offset, firstSplit = true) {
        let didSplit = false;
        if (isUnbreakable(this)) {
            throw UNBREAKABLE_ROLLBACK_CODE;
        }
        let restore;
        if (firstSplit) {
            restore = prepareUpdate(this, offset);
        }

        // First split the node in two and move half the children in the clone.
        const splitEl = this.cloneNode(false);
        while (offset < this.childNodes.length) {
            splitEl.appendChild(this.childNodes[offset]);
        }
        if (isBlock(this) || splitEl.hasChildNodes()) {
            this.after(splitEl);
            if (isVisible(splitEl)) {
                didSplit = true;
            } else {
                splitEl.remove();
            }
        }

        // Propagate the split until reaching a block element (or continue to the
        // closest list item element if there is one).
        if (!isBlock(this) || (this.nodeName !== 'LI' && this.closest('LI'))) {
            if (this.parentElement) {
                this.parentElement.oEnter(childNodeIndex(this) + 1, !didSplit);
            } else {
                // There was no block parent element in the original chain, consider
                // this unsplittable, like an unbreakable.
                throw UNBREAKABLE_ROLLBACK_CODE;
            }
        }

        // All split have been done, place the cursor at the right position, and
        // fill/remove empty nodes.
        if (firstSplit && didSplit) {
            restore();

            fillEmpty(clearEmpty(this));
            fillEmpty(splitEl);

            const focusToElement =
                splitEl.nodeType === Node.ELEMENT_NODE && splitEl.tagName === 'A'
                    ? clearEmpty(splitEl)
                    : splitEl;
            setCursorStart(focusToElement);
        }
        return splitEl;
    };
    /**
     * Specific behavior for headings: do not split in two if cursor at the end but
     * instead create a paragraph.
     * Cursor end of line: <h1>title[]</h1> + ENTER <=> <h1>title</h1><p>[]<br/></p>
     * Cursor in the line: <h1>tit[]le</h1> + ENTER <=> <h1>tit</h1><h1>[]le</h1>
     */
    HTMLHeadingElement.prototype.oEnter = function () {
        const newEl = HTMLElement.prototype.oEnter.call(this, ...arguments);
        if (!newEl.textContent) {
            const node = setTagName(newEl, 'P');
            setCursorStart(node);
        }
    };
    /**
     * Same specific behavior as headings elements.
     */
    HTMLQuoteElement.prototype.oEnter = HTMLHeadingElement.prototype.oEnter;
    /**
     * Specific behavior for list items: deletion and unindentation in some cases.
     */
    HTMLLIElement.prototype.oEnter = function () {
        // If not last list item or not empty last item, regular block split
        if (this.nextElementSibling || this.textContent) {
            const node = HTMLElement.prototype.oEnter.call(this, ...arguments);
            if (node.classList.contains('o_checked')) {
                toggleClass(node, 'o_checked');
            }
            return node;
        }
        this.oShiftTab();
    };
    /**
     * Specific behavior for pre: insert newline (\n) in text or insert p at end.
     */
    HTMLPreElement.prototype.oEnter = function (offset) {
        if (offset < this.childNodes.length) {
            const lineBreak = document.createElement('br');
            this.insertBefore(lineBreak, this.childNodes[offset]);
            setCursorEnd(lineBreak);
        } else {
            const node = document.createElement('p');
            this.parentNode.insertBefore(node, this.nextSibling);
            fillEmpty(node);
            setCursorStart(node);
        }
    };

    Text.prototype.oShiftEnter = function (offset) {
        this.parentElement.oShiftEnter(splitTextNode(this, offset));
    };

    HTMLElement.prototype.oShiftEnter = function (offset) {
        const restore = prepareUpdate(this, offset);

        const brEl = document.createElement('br');
        const brEls = [brEl];
        if (offset >= this.childNodes.length) {
            this.appendChild(brEl);
        } else {
            this.insertBefore(brEl, this.childNodes[offset]);
        }
        if (isFakeLineBreak(brEl) && getState(...leftPos(brEl), DIRECTIONS.LEFT).cType !== CTYPES.BR) {
            const brEl2 = document.createElement('br');
            brEl.before(brEl2);
            brEls.unshift(brEl2);
        }

        restore();

        for (const el of brEls) {
            if (el.parentNode) {
                setCursor(...rightPos(el));
                break;
            }
        }
    };

    Text.prototype.oShiftTab = function () {
        return this.parentElement.oShiftTab(0);
    };

    HTMLElement.prototype.oShiftTab = function (offset = undefined) {
        if (!isUnbreakable(this)) {
            return this.parentElement.oShiftTab(offset);
        }
        return false;
    };

    // returns: is still in a <LI> nested list
    HTMLLIElement.prototype.oShiftTab = function () {
        const li = this;
        if (li.nextElementSibling) {
            const ul = li.parentElement.cloneNode(false);
            while (li.nextSibling) {
                ul.append(li.nextSibling);
            }
            if (li.parentNode.parentNode.tagName === 'LI') {
                const lip = document.createElement('li');
                toggleClass(lip, 'oe-nested');
                lip.append(ul);
                li.parentNode.parentNode.after(lip);
            } else {
                li.parentNode.after(ul);
            }
        }

        const restoreCursor = preserveCursor(this.ownerDocument);
        if (li.parentNode.parentNode.tagName === 'LI') {
            const ul = li.parentNode;
            const shouldRemoveParentLi = !li.previousElementSibling && !ul.previousElementSibling;
            const toremove = shouldRemoveParentLi ? ul.parentNode : null;
            ul.parentNode.after(li);
            if (toremove) {
                if (toremove.classList.contains('oe-nested')) {
                    // <li>content<ul>...</ul></li>
                    toremove.remove();
                } else {
                    // <li class="oe-nested"><ul>...</ul></li>
                    ul.remove();
                }
            }
            restoreCursor();
            return li;
        } else {
            const ul = li.parentNode;
            let p;
            while (li.firstChild) {
                if (isBlock(li.firstChild)) {
                    p = isVisible(p) && ul.after(p) && undefined;
                    ul.after(li.firstChild);
                } else {
                    p = p || document.createElement('P');
                    p.append(li.firstChild);
                }
            }
            if (isVisible(p)) ul.after(p);

            restoreCursor(new Map([[li, ul.nextSibling]]));
            li.remove();
            if (!ul.firstElementChild) {
                ul.remove();
            }
        }
        return false;
    };

    Text.prototype.oTab = function () {
        return this.parentElement.oTab(0);
    };

    HTMLElement.prototype.oTab = function (offset) {
        if (!isBlock(this)) {
            return this.parentElement.oTab(offset);
        }
        return false;
    };

    HTMLLIElement.prototype.oTab = function () {
        const lip = document.createElement('li');
        const destul =
            (this.previousElementSibling && this.previousElementSibling.querySelector('ol, ul')) ||
            (this.nextElementSibling && this.nextElementSibling.querySelector('ol, ul')) ||
            this.closest('ul, ol');

        const ul = createList(getListMode(destul));
        lip.append(ul);

        const cr = preserveCursor(this.ownerDocument);
        toggleClass(lip, 'oe-nested');
        this.before(lip);
        ul.append(this);
        cr();
        return true;
    };

    Text.prototype.oToggleList = function (offset, mode) {
        this.parentElement.oToggleList(childNodeIndex(this), mode);
    };

    HTMLElement.prototype.oToggleList = function (offset, mode = 'UL') {
        if (!isBlock(this)) {
            return this.parentElement.oToggleList(childNodeIndex(this));
        }
        const inLI = this.closest('li');
        if (inLI) {
            return inLI.oToggleList(0, mode);
        }
        const restoreCursor = preserveCursor(this.ownerDocument);
        // if `this` is the root editable
        if (this.oid === 1) {
            const callingNode = this.childNodes[offset];
            const group = getAdjacents(callingNode, n => !isBlock(n));
            insertListAfter(callingNode, mode, [group]);
            restoreCursor();
        } else {
            const list = insertListAfter(this, mode, [this]);
            restoreCursor(new Map([[this, list.firstElementChild]]));
        }
    };

    HTMLParagraphElement.prototype.oToggleList = function (offset, mode = 'UL') {
        const restoreCursor = preserveCursor(this.ownerDocument);
        const list = insertListAfter(this, mode, [[...this.childNodes]]);
        this.remove();

        restoreCursor(new Map([[this, list.firstChild]]));
        return true;
    };

    HTMLLIElement.prototype.oToggleList = function (offset, mode) {
        const pnode = this.closest('ul, ol');
        if (!pnode) return;
        const restoreCursor = preserveCursor(this.ownerDocument);
        const listMode = getListMode(pnode) + mode;
        if (['OLCL', 'ULCL'].includes(listMode)) {
            pnode.classList.add('o_checklist');
            for (let li = pnode.firstElementChild; li !== null; li = li.nextElementSibling) {
                if (li.style.listStyle != 'none') {
                    li.style.listStyle = null;
                    if (!li.style.all) li.removeAttribute('style');
                }
            }
            setTagName(pnode, 'UL');
        } else if (['CLOL', 'CLUL'].includes(listMode)) {
            toggleClass(pnode, 'o_checklist');
            setTagName(pnode, mode);
        } else if (['OLUL', 'ULOL'].includes(listMode)) {
            setTagName(pnode, mode);
        } else {
            // toggle => remove list
            let node = this;
            while (node) {
                node = node.oShiftTab(offset);
            }
        }

        restoreCursor();
        return false;
    };

    HTMLTableCellElement.prototype.oToggleList = function (offset, mode) {
        const restoreCursor = preserveCursor(this.ownerDocument);
        const callingNode = this.childNodes[offset];
        const group = getAdjacents(callingNode, n => !isBlock(n));
        insertListAfter(callingNode, mode, [group]);
        restoreCursor();
    };

    Text.prototype.oAlign = function (offset, mode) {
        this.parentElement.oAlign(childNodeIndex(this), mode);
    };
    /**
     * This does not check for command state
     * @param {*} offset
     * @param {*} mode 'left', 'right', 'center' or 'justify'
     */
    HTMLElement.prototype.oAlign = function (offset, mode) {
        if (!isBlock(this)) {
            return this.parentElement.oAlign(childNodeIndex(this), mode);
        }
        const { textAlign } = getComputedStyle(this);
        const alreadyAlignedLeft = textAlign === 'start' || textAlign === 'left';
        const shouldApplyStyle = !(alreadyAlignedLeft && mode === 'left');
        if (shouldApplyStyle) {
            this.style.textAlign = mode;
        }
    };

    const NOT_A_NUMBER = /[^\d]/g;
    function areSimilarElements(node, node2) {
        if (
            !node ||
            !node2 ||
            node.nodeType !== Node.ELEMENT_NODE ||
            node2.nodeType !== Node.ELEMENT_NODE
        ) {
            return false;
        }
        if (node.tagName !== node2.tagName) {
            return false;
        }
        for (const att of node.attributes) {
            const att2 = node2.attributes[att.name];
            if ((att2 && att2.value) !== att.value) {
                return false;
            }
        }
        for (const att of node2.attributes) {
            const att2 = node.attributes[att.name];
            if ((att2 && att2.value) !== att.value) {
                return false;
            }
        }
        function isNotNoneValue(value) {
            return value && value !== 'none';
        }
        if (
            isNotNoneValue(getComputedStyle(node, ':before').getPropertyValue('content')) ||
            isNotNoneValue(getComputedStyle(node, ':after').getPropertyValue('content')) ||
            isNotNoneValue(getComputedStyle(node2, ':before').getPropertyValue('content')) ||
            isNotNoneValue(getComputedStyle(node2, ':after').getPropertyValue('content'))
        ) {
            return false;
        }
        if (node.tagName == 'LI' && node.classList.contains('oe-nested')) {
            return (
                node.lastElementChild &&
                node2.firstElementChild &&
                getListMode(node.lastElementChild) == getListMode(node2.firstElementChild)
            );
        }
        if (['UL', 'OL'].includes(node.tagName)) {
            return !isVisibleEmpty(node) && !isVisibleEmpty(node2);
        }
        if (isBlock(node) || isVisibleEmpty(node) || isVisibleEmpty(node2)) {
            return false;
        }
        const nodeStyle = getComputedStyle(node);
        const node2Style = getComputedStyle(node2);
        return (
            !+nodeStyle.padding.replace(NOT_A_NUMBER, '') &&
            !+node2Style.padding.replace(NOT_A_NUMBER, '') &&
            !+nodeStyle.margin.replace(NOT_A_NUMBER, '') &&
            !+node2Style.margin.replace(NOT_A_NUMBER, '')
        );
    }

    class Sanitize {
        constructor(root) {
            this.root = root;
            this.parse(root);
        }

        parse(node) {
            node = closestBlock(node);
            if (['UL', 'OL'].includes(node.tagName)) {
                node = node.parentElement;
            }
            this._parse(node);
        }

        _parse(node) {
            if (!node) {
                return;
            }

            // Merge identical elements together
            while (areSimilarElements(node, node.previousSibling)) {
                getDeepRange(this.root, { select: true });
                const restoreCursor = preserveCursor(this.root.ownerDocument);
                const nodeP = node.previousSibling;
                moveNodes(...endPos(node.previousSibling), node);
                restoreCursor();
                node = nodeP;
            }

            // Remove empty blocks in <li>
            if (node.nodeName == 'P' && node.parentElement.tagName == 'LI') {
                const next = node.nextSibling;
                const pnode = node.parentElement;
                if (isEmptyBlock(node)) {
                    const restoreCursor = preserveCursor(this.root.ownerDocument);
                    node.remove();
                    fillEmpty(pnode);
                    this._parse(next);
                    restoreCursor(new Map([[node, pnode]]));
                    return;
                }
            }

            // Sanitize font awesome elements
            if (isFontAwesome(node)) {
                // Ensure a zero width space is present inside the FA element.
                if (node.innerHTML !== '\u200B') node.innerHTML = '&#x200B;';
            }

            // Sanitize media elements
            if (isMediaElement(node)) {
                // Ensure all media elements are tagged contenteditable=false.
                // we cannot use the node.isContentEditable because it can wrongly return false
                // when the editor is starting up ( first sanitize )
                if (node.getAttribute('contenteditable') !== 'false') {
                    node.setAttribute('contenteditable', 'false');
                }
            }

            // FIXME not parse out of editable zone...
            this._parse(node.firstChild);
            this._parse(node.nextSibling);
        }
    }

    function sanitize(root) {
        new Sanitize(root);
        return root;
    }

    // TODO: avoid empty keys when not necessary to reduce request size
    function nodeToObject(node) {
        let result = {
            nodeType: node.nodeType,
            oid: node.oid,
        };
        if (!node.oid) {
            console.warn('OID can not be falsy!');
        }
        if (node.nodeType === Node.TEXT_NODE) {
            result.textValue = node.nodeValue;
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            result.tagName = node.tagName;
            result.children = [];
            result.attributes = {};
            for (let i = 0; i < node.attributes.length; i++) {
                result.attributes[node.attributes[i].name] = node.attributes[i].value;
            }
            let child = node.firstChild;
            while (child) {
                result.children.push(nodeToObject(child));
                child = child.nextSibling;
            }
        }
        return result;
    }

    function objectToNode(obj) {
        let result = undefined;
        if (obj.nodeType === Node.TEXT_NODE) {
            result = document.createTextNode(obj.textValue);
        } else if (obj.nodeType === Node.ELEMENT_NODE) {
            result = document.createElement(obj.tagName);
            for (const key in obj.attributes) {
                result.setAttribute(key, obj.attributes[key]);
            }
            obj.children.forEach(child => result.append(objectToNode(child)));
        } else {
            console.warn('unknown node type');
        }
        result.oid = obj.oid;
        return result;
    }

    const TEXT_CLASSES_REGEX = /\btext-[^\s]*\b/g;
    const BG_CLASSES_REGEX = /\bbg-[^\s]*\b/g;

    function insert(editor, data, isText = true) {
        const selection = editor.document.getSelection();
        const range = selection.getRangeAt(0);
        let startNode;
        let insertBefore = false;
        if (selection.isCollapsed) {
            if (range.startContainer.nodeType === Node.TEXT_NODE) {
                insertBefore = !range.startOffset;
                splitTextNode(range.startContainer, range.startOffset, DIRECTIONS.LEFT);
                startNode = range.startContainer;
            }
        } else {
            editor.deleteRange(selection);
        }
        startNode = startNode || editor.document.getSelection().anchorNode;
        if (startNode.nodeType === Node.ELEMENT_NODE) {
            if (selection.anchorOffset === 0) {
                startNode.prepend(editor.document.createTextNode(''));
                startNode = startNode.firstChild;
            } else {
                startNode = startNode.childNodes[selection.anchorOffset - 1];
            }
        }

        const fakeEl = document.createElement('fake-element');
        if (isText) {
            fakeEl.innerText = data;
        } else {
            fakeEl.innerHTML = data;
        }
        let nodeToInsert;
        const insertedNodes = [...fakeEl.childNodes];
        while ((nodeToInsert = fakeEl.childNodes[0])) {
            if (insertBefore) {
                startNode.before(nodeToInsert);
                insertBefore = false;
            } else {
                startNode.after(nodeToInsert);
            }
            startNode = nodeToInsert;
        }

        selection.removeAllRanges();
        const newRange = new Range();
        const lastPosition = rightPos(startNode);
        newRange.setStart(lastPosition[0], lastPosition[1]);
        newRange.setEnd(lastPosition[0], lastPosition[1]);
        selection.addRange(newRange);
        return insertedNodes;
    }
    function align(editor, mode) {
        const sel = editor.document.getSelection();
        const visitedBlocks = new Set();
        const traversedNode = getTraversedNodes(editor.editable);
        for (const node of traversedNode) {
            if (isContentTextNode(node) && isVisible(node)) {
                const block = closestBlock(node);
                if (!visitedBlocks.has(block)) {
                    const hasModifier = getComputedStyle(block).textAlign === mode;
                    if (!hasModifier && block.isContentEditable) {
                        block.oAlign(sel.anchorOffset, mode);
                    }
                    visitedBlocks.add(block);
                }
            }
        }
    }

    /**
     * Applies a css or class color (fore- or background-) to an element.
     * Replace the color that was already there if any.
     *
     * @param {Element} element
     * @param {string} color hexadecimal or bg-name/text-name class
     * @param {string} mode 'color' or 'backgroundColor'
     */
    function colorElement(element, color, mode) {
        const newClassName = element.className
            .replace(mode === 'color' ? TEXT_CLASSES_REGEX : BG_CLASSES_REGEX, '')
            .replace(/\s+/, ' ');
        element.className !== newClassName && (element.className = newClassName);
        if (color.startsWith('text') || color.startsWith('bg-')) {
            element.style[mode] = '';
            element.className += ' ' + color;
        } else {
            element.style[mode] = color;
        }
    }

    /**
     * Returns true if the given element has a visible color (fore- or
     * -background depending on the given mode).
     *
     * @param {Element} element
     * @param {string} mode 'color' or 'backgroundColor'
     * @returns {boolean}
     */
    function hasColor(element, mode) {
        const style = element.style;
        const parent = element.parentNode;
        const classRegex = mode === 'color' ? TEXT_CLASSES_REGEX : BG_CLASSES_REGEX;
        return (
            (style[mode] && style[mode] !== 'inherit' && style[mode] !== parent.style[mode]) ||
            (classRegex.test(element.className) &&
                getComputedStyle(element)[mode] !== getComputedStyle(parent)[mode])
        );
    }
    /**
     * This function abstracts the difficulty of applying a inline style to a
     * selection. TODO: This implementations potentially adds one span per text
     * node, in an ideal world it would wrap all concerned nodes in one span
     * whenever possible.
     * @param {Element => void} applyStyle Callback that receives an element to
     * which the wanted style should be applied
     */
    function applyInlineStyle(editor, applyStyle) {
        const sel = editor.document.getSelection();
        const { startContainer, startOffset, endContainer, endOffset } = sel.getRangeAt(0);
        const { anchorNode, anchorOffset, focusNode, focusOffset } = sel;
        const direction = getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset);
        const selectedTextNodes = getTraversedNodes(editor.editable).filter(node =>
            isContentTextNode(node),
        );
        for (const textNode of selectedTextNodes) {
            const atLeastOneCharFromNodeInSelection = !(
                (textNode === endContainer && endOffset === 0) ||
                (textNode === startContainer && startOffset === textNode.textContent.length)
            );
            // If text node ends after the end of the selection, split it and
            // keep the part that is inside.
            if (endContainer === textNode && endOffset < textNode.textContent.length) {
                // No reassignement needed, entirely dependent on the
                // splitTextNode implementation.
                splitTextNode(textNode, endOffset, DIRECTIONS.LEFT);
            }
            // If text node starts before the beginning of the selection, split it
            // and keep the part that is inside as textNode.
            if (startContainer === textNode && startOffset > 0) {
                // No reassignement needed, entirely dependent on the
                // splitTextNode implementation.
                splitTextNode(textNode, startOffset, DIRECTIONS.RIGHT);
            }
            // If the parent is not inline or is not completely in the
            // selection, wrap text node in inline node. Also skips <a> tags to
            // work with native `removeFormat` command
            if (
                atLeastOneCharFromNodeInSelection &&
                (isBlock(textNode.parentElement) ||
                    (textNode === endContainer && textNode.nextSibling) ||
                    (textNode === startContainer && textNode.previousSibling) ||
                    textNode.parentElement.tagName === 'A')
            ) {
                const newParent = document.createElement('span');
                textNode.after(newParent);
                newParent.appendChild(textNode);
            }
            // Make sure there's at least one char selected in the text node
            if (atLeastOneCharFromNodeInSelection) {
                applyStyle(textNode.parentElement);
            }
        }
        if (direction === DIRECTIONS.RIGHT) {
            setCursor(startContainer, 0, endContainer, endOffset);
        } else {
            setCursor(endContainer, endOffset, startContainer, 0);
        }
    }
    function addColumn(editor, beforeOrAfter) {
        getDeepRange(editor.editable, { select: true }); // Ensure deep range for finding td.
        const c = getInSelection(editor.document, 'td');
        if (!c) return;
        const i = [...closestElement(c, 'tr').querySelectorAll('th, td')].findIndex(td => td === c);
        const column = closestElement(c, 'table').querySelectorAll(`tr td:nth-of-type(${i + 1})`);
        column.forEach(row => row[beforeOrAfter](document.createElement('td')));
    }
    function addRow(editor, beforeOrAfter) {
        getDeepRange(editor.editable, { select: true }); // Ensure deep range for finding tr.
        const row = getInSelection(editor.document, 'tr');
        if (!row) return;
        const newRow = document.createElement('tr');
        const cells = row.querySelectorAll('td');
        newRow.append(...Array.from(Array(cells.length)).map(() => document.createElement('td')));
        row[beforeOrAfter](newRow);
    }
    function deleteTable(editor, table) {
        table = table || getInSelection(editor.document, 'table');
        if (!table) return;
        const p = document.createElement('p');
        p.appendChild(document.createElement('br'));
        table.before(p);
        table.remove();
        setCursor(p, 0);
    }

    // This is a whitelist of the commands that are implemented by the
    // editor itself rather than the node prototypes. It might be
    // possible to switch the conditions and test if the method exist on
    // `sel.anchorNode` rather than relying on an expicit whitelist, but
    // the behavior would change if a method name exists both on the
    // editor and on the nodes. This is too risky to change in the
    // absence of a strong test suite, so the whitelist stays for now.
    const editorCommands = {
        // Insertion
        insertHTML: (editor, data) => {
            return insert(editor, data, false);
        },
        insertText: (editor, data) => {
            return insert(editor, data);
        },
        insertFontAwesome: (editor, faClass = 'fa fa-star') => {
            const insertedNode = editorCommands.insertHTML(editor, '<i></i>')[0];
            insertedNode.className = faClass;
            const position = rightPos(insertedNode);
            setCursor(...position, ...position, false);
        },

        // History
        undo: editor => editor.historyUndo(),
        redo: editor => editor.historyRedo(),

        // Change tags
        setTag(editor, tagName) {
            const restoreCursor = preserveCursor(editor.document);
            const selectedBlocks = [...new Set(getTraversedNodes(editor.editable).map(closestBlock))];
            for (const selectedBlock of selectedBlocks) {
                const block = closestBlock(selectedBlock);
                if (
                    ['P', 'PRE', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'BLOCKQUOTE'].includes(
                        block.nodeName,
                    )
                ) {
                    setTagName(block, tagName);
                } else {
                    // eg do not change a <div> into a h1: insert the h1
                    // into it instead.
                    const newBlock = editor.document.createElement(tagName);
                    const children = [...block.childNodes];
                    block.insertBefore(newBlock, block.firstChild);
                    children.forEach(child => newBlock.appendChild(child));
                }
            }
            restoreCursor();
        },

        // Formats
        // -------------------------------------------------------------------------
        bold: editor => {
            const selection = editor.document.getSelection();
            if (!selection.rangeCount || selection.getRangeAt(0).collapsed) return;
            getDeepRange(editor.editable, { splitText: true, select: true, correctTripleClick: true });
            const isAlreadyBold = getSelectedNodes(editor.editable)
                .filter(n => n.nodeType === Node.TEXT_NODE && n.nodeValue.trim().length)
                .find(n => Number.parseInt(getComputedStyle(n.parentElement).fontWeight) > 500);
            applyInlineStyle(editor, el => {
                el.style.fontWeight = isAlreadyBold ? 'normal' : 'bolder';
            });
        },
        italic: editor => editor.document.execCommand('italic'),
        underline: editor => editor.document.execCommand('underline'),
        strikeThrough: editor => editor.document.execCommand('strikeThrough'),
        removeFormat: editor => editor.document.execCommand('removeFormat'),

        // Align
        justifyLeft: editor => align(editor, 'left'),
        justifyRight: editor => align(editor, 'right'),
        justifyCenter: editor => align(editor, 'center'),
        justifyFull: editor => align(editor, 'justify'),
        /**
         * @param {string} size A valid css size string
         */
        setFontSize: (editor, size) => {
            const selection = editor.document.getSelection();
            if (!selection.rangeCount || selection.getRangeAt(0).collapsed) return;
            applyInlineStyle(editor, element => {
                element.style.fontSize = size;
            });
        },

        // Link
        createLink: (editor, link, content) => {
            const sel = editor.document.getSelection();
            if (content && !sel.isCollapsed) {
                editor.deleteRange(sel);
            }
            if (sel.isCollapsed) {
                insertText(sel, content || 'link');
            }
            const currentLink = closestElement(sel.focusNode, 'a');
            link = link || prompt('URL or Email', (currentLink && currentLink.href) || 'http://');
            const res = editor.document.execCommand('createLink', false, link);
            if (res) {
                setCursor(sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset);
                const node = findNode(closestPath(sel.focusNode), node => node.tagName === 'A');
                const pos = [node.parentElement, childNodeIndex(node) + 1];
                setCursor(...pos, ...pos, false);
            }
        },
        unlink: editor => {
            const sel = editor.document.getSelection();
            // we need to remove the contentEditable isolation of links
            // before we apply the unlink, otherwise the command is not performed
            // because the content editable root is the link
            const closestEl = closestElement(sel.focusNode);
            if (closestEl.tagName === 'A' && closestEl.getAttribute('contenteditable') === 'true') {
                editor._activateContenteditable();
            }
            if (sel.isCollapsed) {
                const cr = preserveCursor(editor.document);
                const node = closestElement(sel.focusNode, 'a');
                setCursor(node, 0, node, node.childNodes.length, false);
                editor.document.execCommand('unlink');
                cr();
            } else {
                editor.document.execCommand('unlink');
                setCursor(sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset);
            }
        },

        // List
        indentList: (editor, mode = 'indent') => {
            const [pos1, pos2] = getCursors(editor.document);
            const end = leftDeepFirstPath(...pos1).next().value;
            const li = new Set();
            for (const node of leftDeepFirstPath(...pos2)) {
                const cli = closestBlock(node);
                if (
                    cli &&
                    cli.tagName == 'LI' &&
                    !li.has(cli) &&
                    !cli.classList.contains('oe-nested')
                ) {
                    li.add(cli);
                }
                if (node == end) break;
            }
            for (const node of li) {
                if (mode == 'indent') {
                    node.oTab(0);
                } else {
                    node.oShiftTab(0);
                }
            }
            return true;
        },
        toggleList: (editor, mode) => {
            const li = new Set();
            const blocks = new Set();

            for (const node of getTraversedNodes(editor.editable)) {
                const block = closestBlock(node);
                if (!['OL', 'UL'].includes(block.tagName)) {
                    const ublock = block.closest('ol, ul');
                    ublock && getListMode(ublock) == mode ? li.add(block) : blocks.add(block);
                }
            }

            let target = [...(blocks.size ? blocks : li)];
            while (target.length) {
                const node = target.pop();
                // only apply one li per ul
                if (!node.oToggleList(0, mode)) {
                    target = target.filter(
                        li => li.parentNode != node.parentNode || li.tagName != 'LI',
                    );
                }
            }
        },

        /**
         * Apply a css or class color on the current selection (wrapped in <font>).
         *
         * @param {string} color hexadecimal or bg-name/text-name class
         * @param {string} mode 'color' or 'backgroundColor'
         * @param {Element} [element]
         */
        applyColor: (editor, color, mode, element) => {
            if (element) {
                colorElement(element, color, mode);
                return;
            }
            const range = getDeepRange(editor.editable, { splitText: true, select: true });
            if (!range) return;
            const restoreCursor = preserveCursor(editor.document);
            // Get the <font> nodes to color
            const selectedNodes = getSelectedNodes(editor.editable);
            const fonts = selectedNodes.flatMap(node => {
                let font = closestElement(node, 'font');
                const children = font && [...font.childNodes];
                if (font && font.nodeName === 'FONT') {
                    // Partially selected <font>: split it.
                    const selectedChildren = children.filter(child => selectedNodes.includes(child));
                    const after = selectedChildren[selectedChildren.length - 1].nextSibling;
                    font = after ? splitElement(font, childNodeIndex(after))[0] : font;
                    const before = selectedChildren[0].previousSibling;
                    font = before ? splitElement(font, childNodeIndex(before) + 1)[1] : font;
                } else if (node.nodeType === Node.TEXT_NODE && isVisibleStr(node)) {
                    // Node is a visible text node: wrap it in a <font>.
                    const previous = node.previousSibling;
                    const classRegex = mode === 'color' ? BG_CLASSES_REGEX : TEXT_CLASSES_REGEX;
                    if (
                        previous &&
                        previous.nodeName === 'FONT' &&
                        !previous.style[mode === 'color' ? 'backgroundColor' : 'color'] &&
                        !classRegex.test(previous.className) &&
                        selectedNodes.includes(previous.firstChild) &&
                        selectedNodes.includes(previous.lastChild)
                    ) {
                        // Directly follows a fully selected <font> that isn't
                        // colored in the other mode: append to that.
                        font = previous;
                    } else {
                        // No <font> found: insert a new one.
                        font = document.createElement('font');
                        node.parentNode.insertBefore(font, node);
                    }
                    font.appendChild(node);
                } else {
                    font = []; // Ignore non-text or invisible text nodes.
                }
                return font;
            });
            // Color the selected <font>s and remove uncolored fonts.
            for (const font of new Set(fonts)) {
                colorElement(font, color, mode);
                if (!hasColor(font, mode) && !hasColor(font, mode)) {
                    for (const child of [...font.childNodes]) {
                        font.parentNode.insertBefore(child, font);
                    }
                    font.parentNode.removeChild(font);
                }
            }
            restoreCursor();
        },
        // Table
        insertTable: (editor, { rowCount = 2, colCount = 2 } = {}) => {
            const tdsHtml = new Array(colCount).fill('<td><br></td>').join('');
            const trsHtml = new Array(rowCount).fill(`<tr>${tdsHtml}</tr>`).join('');
            const tableHtml = `<table class="table table-bordered"><tbody>${trsHtml}</tbody></table>`;
            const sel = editor.document.getSelection();
            if (!sel.isCollapsed) {
                editor.deleteRange(sel);
            }
            while (!isBlock(sel.anchorNode)) {
                const anchorNode = sel.anchorNode;
                const isTextNode = anchorNode.nodeType === Node.TEXT_NODE;
                const newAnchorNode = isTextNode
                    ? splitTextNode(anchorNode, sel.anchorOffset, DIRECTIONS.LEFT) + 1 && anchorNode
                    : splitElement(anchorNode, sel.anchorOffset).shift();
                const newPosition = rightPos(newAnchorNode);
                setCursor(...newPosition, ...newPosition, false);
            }
            const [table] = editorCommands.insertHTML(editor, tableHtml);
            setCursorStart(table.querySelector('td'));
        },
        addColumnLeft: editor => {
            addColumn(editor, 'before');
        },
        addColumnRight: editor => {
            addColumn(editor, 'after');
        },
        addRowAbove: editor => {
            addRow(editor, 'before');
        },
        addRowBelow: editor => {
            addRow(editor, 'after');
        },
        removeColumn: editor => {
            getDeepRange(editor.editable, { select: true }); // Ensure deep range for finding td.
            const cell = getInSelection(editor.document, 'td');
            if (!cell) return;
            const table = closestElement(cell, 'table');
            const cells = [...closestElement(cell, 'tr').querySelectorAll('th, td')];
            const index = cells.findIndex(td => td === cell);
            const siblingCell = cells[index - 1] || cells[index + 1];
            table.querySelectorAll(`tr td:nth-of-type(${index + 1})`).forEach(td => td.remove());
            siblingCell ? setCursor(...startPos(siblingCell)) : deleteTable(editor, table);
        },
        removeRow: editor => {
            getDeepRange(editor.editable, { select: true }); // Ensure deep range for finding tr.
            const row = getInSelection(editor.document, 'tr');
            if (!row) return;
            const table = closestElement(row, 'table');
            const rows = [...table.querySelectorAll('tr')];
            const rowIndex = rows.findIndex(tr => tr === row);
            const siblingRow = rows[rowIndex - 1] || rows[rowIndex + 1];
            row.remove();
            siblingRow ? setCursor(...startPos(siblingRow)) : deleteTable(editor, table);
        },
        deleteTable: (editor, table) => deleteTable(editor, table),
    };

    const UNBREAKABLE_ROLLBACK_CODE = 'UNBREAKABLE';
    const UNREMOVABLE_ROLLBACK_CODE = 'UNREMOVABLE';
    const BACKSPACE_ONLY_COMMANDS = ['oDeleteBackward', 'oDeleteForward'];
    const BACKSPACE_FIRST_COMMANDS = BACKSPACE_ONLY_COMMANDS.concat(['oEnter', 'oShiftEnter']);

    const TABLEPICKER_ROW_COUNT = 3;
    const TABLEPICKER_COL_COUNT = 3;

    const KEYBOARD_TYPES = { VIRTUAL: 'VIRTUAL', PHYSICAL: 'PHYSICAL', UNKNOWN: 'UKNOWN' };

    const isUndo = ev => ev.key === 'z' && (ev.ctrlKey || ev.metaKey);
    const isRedo = ev => ev.key === 'y' && (ev.ctrlKey || ev.metaKey);

    function defaultOptions(defaultObject, object) {
        const newObject = Object.assign({}, defaultObject, object);
        for (const [key, value] of Object.entries(object)) {
            if (typeof value === 'undefined') {
                newObject[key] = defaultObject[key];
            }
        }
        return newObject;
    }

    class OdooEditor extends EventTarget {
        constructor(editable, options = {}) {
            super();

            this.options = defaultOptions(
                {
                    controlHistoryFromDocument: false,
                    getContextFromParentRect: () => {
                        return { top: 0, left: 0 };
                    },
                    toSanitize: true,
                    isRootEditable: true,
                    getContentEditableAreas: () => [],
                },
                options,
            );

            // --------------
            // Set properties
            // --------------

            this.document = options.document || document;

            this.isMobile = matchMedia('(max-width: 767px)').matches;

            // Keyboard type detection, happens only at the first keydown event.
            this.keyboardType = KEYBOARD_TYPES.UNKNOWN;

            // Wether we should check for unbreakable the next history step.
            this._checkStepUnbreakable = true;

            // All dom listeners currently active.
            this._domListeners = [];

            this.resetHistory();

            // Set of labels that which prevent the automatic step mechanism if
            // it contains at least one element.
            this._observerTimeoutUnactive = new Set();
            // Set of labels that which prevent the observer to be active if
            // it contains at least one element.
            this._observerUnactiveLabels = new Set();

            // The state of the dom.
            this._currentMouseState = 'mouseup';

            this._onKeyupResetContenteditableNodes = [];

            this._isCollaborativeActive = false;
            this._collaborativeLastSynchronisedId = null;

            // Track if we need to rollback mutations in case unbreakable or unremovable are being added or removed.
            this._toRollback = false;

            // Map that from an node id to the dom node.
            this._idToNodeMap = new Map();

            // -------------------
            // Alter the editable
            // -------------------

            if (editable.innerHTML.trim() === '') {
                editable.innerHTML = '<p><br></p>';
            }

            // Convention: root node is ID 1.
            editable.oid = 1;
            this._idToNodeMap.set(1, editable);
            this.editable = this.options.toSanitize ? sanitize(editable) : editable;

            // Set contenteditable before clone as FF updates the content at this point.
            this._activateContenteditable();

            this.idSet(editable);

            // -----------
            // Bind events
            // -----------

            this.observerActive();

            this.addDomListener(this.editable, 'keydown', this._onKeyDown);
            this.addDomListener(this.editable, 'input', this._onInput);
            this.addDomListener(this.editable, 'mousedown', this._onMouseDown);
            this.addDomListener(this.editable, 'mouseup', this._onMouseup);
            this.addDomListener(this.editable, 'paste', this._onPaste);
            this.addDomListener(this.editable, 'drop', this._onDrop);

            this.addDomListener(this.document, 'selectionchange', this._onSelectionChange);
            this.addDomListener(this.document, 'keydown', this._onDocumentKeydown);
            this.addDomListener(this.document, 'keyup', this._onDocumentKeyup);

            // -------
            // Toolbar
            // -------

            if (this.options.toolbar) {
                this.toolbar = this.options.toolbar;
                this._bindToolbar();
                // Ensure anchors in the toolbar don't trigger a hash change.
                const toolbarAnchors = this.toolbar.querySelectorAll('a');
                toolbarAnchors.forEach(a => a.addEventListener('click', e => e.preventDefault()));
                this.tablePicker = this.toolbar.querySelector('.tablepicker');
                if (this.tablePicker) {
                    this.tablePickerSizeView = this.toolbar.querySelector('.tablepicker-size');
                    this.toolbar
                        .querySelector('#tableDropdownButton')
                        .addEventListener('click', this._initTablePicker.bind(this));
                }
                for (const colorLabel of this.toolbar.querySelectorAll('label')) {
                    colorLabel.addEventListener('mousedown', ev => {
                        // Hack to prevent loss of focus (done by preventDefault) while still opening
                        // color picker dialog (which is also prevented by preventDefault on chrome,
                        // except when click detail is 2, which happens on a double-click but isn't
                        // triggered by a dblclick event)
                        if (ev.detail < 2) {
                            ev.preventDefault();
                            ev.currentTarget.dispatchEvent(new MouseEvent('click', { detail: 2 }));
                        }
                    });
                    colorLabel.addEventListener('input', ev => {
                        this.document.execCommand(ev.target.name, false, ev.target.value);
                        this.updateColorpickerLabels();
                    });
                }
                if (this.isMobile) {
                    this.editable.before(this.toolbar);
                }
            }
        }
        /**
         * Releases anything that was initialized.
         *
         * TODO: properly implement this.
         */
        destroy() {
            this.observerUnactive();
            this._removeDomListener();
        }

        sanitize() {
            this.observerFlush();

            // find common ancestror in this.history[-1]
            const step = this._historySteps[this._historySteps.length - 1];
            let commonAncestor, record;
            for (record of step.mutations) {
                const node = this.idFind(record.parentId || record.id) || this.editable;
                commonAncestor = commonAncestor
                    ? commonParentGet(commonAncestor, node, this.editable)
                    : node;
            }
            if (!commonAncestor) {
                return false;
            }

            // sanitize and mark current position as sanitized
            sanitize(commonAncestor);
        }

        addDomListener(element, eventName, callback) {
            const boundCallback = callback.bind(this);
            this._domListeners.push([element, eventName, boundCallback]);
            element.addEventListener(eventName, boundCallback);
        }

        // Assign IDs to src, and dest if defined
        idSet(node, testunbreak = false) {
            if (!node.oid) {
                node.oid = (Math.random() * 2 ** 31) | 0; // TODO: uuid4 or higher number
                this._idToNodeMap.set(node.oid, node);
            }
            // Rollback if node.ouid changed. This ensures that nodes never change
            // unbreakable ancestors.
            node.ouid = node.ouid || getOuid(node, true);
            if (testunbreak) {
                const ouid = getOuid(node);
                if (!this._toRollback && ouid && ouid !== node.ouid) {
                    this._toRollback = UNBREAKABLE_ROLLBACK_CODE;
                }
            }

            let childNode = node.firstChild;
            while (childNode) {
                this.idSet(childNode, testunbreak);
                childNode = childNode.nextSibling;
            }
        }

        idFind(id) {
            return this._idToNodeMap.get(id);
        }

        // Observer that syncs doms

        // if not in collaboration mode, no need to serialize / unserialize
        serialize(node) {
            return this._isCollaborativeActive ? nodeToObject(node) : node;
        }
        unserialize(obj) {
            return this._isCollaborativeActive ? objectToNode(obj) : obj;
        }

        automaticStepActive(label) {
            this._observerTimeoutUnactive.delete(label);
        }
        automaticStepUnactive(label) {
            this._observerTimeoutUnactive.add(label);
        }
        automaticStepSkipStack() {
            this.automaticStepUnactive('skipStack');
            setTimeout(() => this.automaticStepActive('skipStack'));
        }
        observerUnactive(label) {
            this._observerUnactiveLabels.add(label);
            clearTimeout(this.observerTimeout);
            this.observer.disconnect();
            this.observerFlush();
        }
        observerFlush() {
            this.observerApply(this.observer.takeRecords());
        }
        observerActive(label) {
            this._observerUnactiveLabels.delete(label);
            if (this._observerUnactiveLabels.size !== 0) return;

            if (!this.observer) {
                this.observer = new MutationObserver(records => {
                    records = this.filterMutationRecords(records);
                    if (!records.length) return;
                    clearTimeout(this.observerTimeout);
                    if (this._observerTimeoutUnactive.size === 0) {
                        this.observerTimeout = setTimeout(() => {
                            this.historyStep();
                        }, 100);
                    }
                    this.observerApply(records);
                });
            }
            this.observer.observe(this.editable, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeOldValue: true,
                characterData: true,
                characterDataOldValue: true,
            });
        }

        observerApply(records) {
            for (const record of records) {
                switch (record.type) {
                    case 'characterData': {
                        this._historySteps[this._historySteps.length - 1].mutations.push({
                            'type': 'characterData',
                            'id': record.target.oid,
                            'text': record.target.textContent,
                            'oldValue': record.oldValue,
                        });
                        break;
                    }
                    case 'attributes': {
                        this._historySteps[this._historySteps.length - 1].mutations.push({
                            'type': 'attributes',
                            'id': record.target.oid,
                            'attributeName': record.attributeName,
                            'value': record.target.getAttribute(record.attributeName),
                            'oldValue': record.oldValue,
                        });
                        break;
                    }
                    case 'childList': {
                        record.addedNodes.forEach(added => {
                            this._toRollback =
                                this._toRollback ||
                                (containsUnremovable(added) && UNREMOVABLE_ROLLBACK_CODE);
                            const mutation = {
                                'type': 'add',
                            };
                            if (!record.nextSibling && record.target.oid) {
                                mutation.append = record.target.oid;
                            } else if (record.nextSibling && record.nextSibling.oid) {
                                mutation.before = record.nextSibling.oid;
                            } else if (!record.previousSibling && record.target.oid) {
                                mutation.prepend = record.target.oid;
                            } else if (record.previousSibling && record.previousSibling.oid) {
                                mutation.after = record.previousSibling.oid;
                            } else {
                                return false;
                            }
                            this.idSet(added, this._checkStepUnbreakable);
                            mutation.id = added.oid;
                            mutation.node = this.serialize(added);
                            this._historySteps[this._historySteps.length - 1].mutations.push(mutation);
                        });
                        record.removedNodes.forEach(removed => {
                            if (!this._toRollback && containsUnremovable(removed)) {
                                this._toRollback = UNREMOVABLE_ROLLBACK_CODE;
                            }
                            this._historySteps[this._historySteps.length - 1].mutations.push({
                                'type': 'remove',
                                'id': removed.oid,
                                'parentId': record.target.oid,
                                'node': this.serialize(removed),
                                'nextId': record.nextSibling ? record.nextSibling.oid : undefined,
                                'previousId': record.previousSibling
                                    ? record.previousSibling.oid
                                    : undefined,
                            });
                        });
                        break;
                    }
                }
            }
            this.dispatchEvent(new Event('observerApply'));
        }
        filterMutationRecords(records) {
            // Save the first attribute in a cache to compare only the first
            // attribute record of node to its latest state.
            const attributeCache = new Map();
            const filteredRecords = [];

            for (const record of records) {
                if (record.type === 'attributes') {
                    // Skip the attributes change on the dom.
                    if (record.target === this.editable) continue;

                    attributeCache.set(record.target, attributeCache.get(record.target) || {});
                    if (
                        typeof attributeCache.get(record.target)[record.attributeName] === 'undefined'
                    ) {
                        const oldValue = record.oldValue === undefined ? null : record.oldValue;
                        attributeCache.get(record.target)[record.attributeName] =
                            oldValue !== record.target.getAttribute(record.attributeName);
                    }
                    if (!attributeCache.get(record.target)[record.attributeName]) {
                        continue;
                    }
                }
                filteredRecords.push(record);
            }
            return filteredRecords;
        }

        resetHistory() {
            this._historySteps = [
                {
                    cursor: {
                        // cursor at beginning of step
                        anchorNode: undefined,
                        anchorOffset: undefined,
                        focusNode: undefined,
                        focusOffset: undefined,
                    },
                    mutations: [],
                    id: undefined,
                },
            ];
            this._historyStepsStates = new Map();
        }
        //
        // History
        //

        // One step completed: apply to vDOM, setup next history step
        historyStep(skipRollback = false) {
            this.observerFlush();
            // check that not two unBreakables modified
            if (this._toRollback) {
                if (!skipRollback) this.historyRollback();
                this._toRollback = false;
            }

            // push history
            const latest = this._historySteps[this._historySteps.length - 1];
            if (!latest.mutations.length) {
                return false;
            }

            latest.id = (Math.random() * 2 ** 31) | 0; // TODO: replace by uuid4 generator
            this.historySend(latest);
            this._historySteps.push({
                cursor: {},
                mutations: [],
            });
            this._checkStepUnbreakable = true;
            this._recordHistoryCursor();
            this.dispatchEvent(new Event('historyStep'));
        }

        // apply changes according to some records
        historyApply(records) {
            for (const record of records) {
                if (record.type === 'characterData') {
                    const node = this.idFind(record.id);
                    if (node) {
                        node.textContent = record.text;
                    }
                } else if (record.type === 'attributes') {
                    const node = this.idFind(record.id);
                    if (node) {
                        node.setAttribute(record.attributeName, record.value);
                    }
                } else if (record.type === 'remove') {
                    const toremove = this.idFind(record.id);
                    if (toremove) {
                        toremove.remove();
                    }
                } else if (record.type === 'add') {
                    const node = this.unserialize(record.node);
                    const newnode = node.cloneNode(1);
                    // preserve oid after the clone
                    this.idSet(node, newnode);

                    const destnode = this.idFind(record.node.oid);
                    if (destnode && record.node.parentNode.oid === destnode.parentNode.oid) {
                        // TODO: optimization: remove record from the history to reduce collaboration bandwidth
                        continue;
                    }
                    if (record.append && this.idFind(record.append)) {
                        this.idFind(record.append).append(newnode);
                    } else if (record.before && this.idFind(record.before)) {
                        this.idFind(record.before).before(newnode);
                    } else if (record.after && this.idFind(record.after)) {
                        this.idFind(record.after).after(newnode);
                    } else {
                        continue;
                    }
                }
            }
        }

        // send changes to server
        historyFetch() {
            if (!this._isCollaborativeActive) {
                return;
            }
            window
                .fetch(`/history-get/${this._collaborativeLastSynchronisedId || 0}`, {
                    headers: { 'Content-Type': 'application/json;charset=utf-8' },
                    method: 'GET',
                })
                .then(response => {
                    if (!response.ok) {
                        return Promise.reject();
                    }
                    return response.json();
                })
                .then(result => {
                    if (!result.length) {
                        return false;
                    }
                    this.observerUnactive();

                    let index = this._historySteps.length;
                    let updated = false;
                    while (
                        index &&
                        this._historySteps[index - 1].id !== this._collaborativeLastSynchronisedId
                    ) {
                        index--;
                    }

                    for (let residx = 0; residx < result.length; residx++) {
                        const record = result[residx];
                        this._collaborativeLastSynchronisedId = record.id;
                        if (
                            index < this._historySteps.length &&
                            record.id === this._historySteps[index].id
                        ) {
                            index++;
                            continue;
                        }
                        updated = true;

                        // we are not synched with the server anymore, rollback and replay
                        while (this._historySteps.length > index) {
                            this.historyRollback();
                            this._historySteps.pop();
                        }

                        if (record.id === 1) {
                            this.editable.innerHTML = '';
                        }
                        this.historyApply(record.mutations);

                        record.mutations = record.id === 1 ? [] : record.mutations;
                        this._historySteps.push(record);
                        index++;
                    }
                    if (updated) {
                        this._historySteps.push({
                            cursor: {},
                            mutations: [],
                        });
                    }
                    this.observerActive();
                    this.historyFetch();
                })
                .catch(() => {
                    // TODO: change that. currently: if error on fetch, fault back to non collaborative mode.
                    this._isCollaborativeActive = false;
                });
        }

        historySend(item) {
            if (!this._isCollaborativeActive) {
                return;
            }
            window.fetch('/history-push', {
                body: JSON.stringify(item),
                headers: { 'Content-Type': 'application/json;charset=utf-8' },
                method: 'POST',
            });
        }

        historyRollback(until = 0) {
            const step = this._historySteps[this._historySteps.length - 1];
            this.observerFlush();
            this.historyRevert(step, until);
            this.observerFlush();
            step.mutations = step.mutations.slice(0, until);
            this._toRollback = false;
        }

        /**
         * Undo a step of the history.
         *
         * this._historyStepsState is a map from it's location (index) in this.history to a state.
         * The state can be on of:
         * undefined: the position has never been undo or redo.
         * 0: The position is considered as a redo of another.
         * 1: The position is considered as a undo of another.
         * 2: The position has been undone and is considered consumed.
         */
        historyUndo() {
            // The last step is considered an uncommited draft so always revert it.
            const lastStep = this._historySteps[this._historySteps.length - 1];
            this.historyRevert(lastStep);
            // Clean the last step otherwise if no other step is created after, the
            // mutations of the revert itself will be added to the same step and
            // grow exponentially at each undo.
            lastStep.mutations = [];

            const pos = this._getNextUndoIndex();
            if (pos >= 0) {
                // Consider the position consumed.
                this._historyStepsStates.set(pos, 2);
                this.historyRevert(this._historySteps[pos]);
                // Consider the last position of the history as an undo.
                this._historyStepsStates.set(this._historySteps.length - 1, 1);
                this.historyStep(true);
                this.dispatchEvent(new Event('historyUndo'));
            }
        }

        /**
         * Redo a step of the history.
         *
         * @see historyUndo
         */
        historyRedo() {
            const pos = this._getNextRedoIndex();
            if (pos >= 0) {
                this._historyStepsStates.set(pos, 2);
                this.historyRevert(this._historySteps[pos]);
                this._historyStepsStates.set(this._historySteps.length - 1, 0);
                this.historySetCursor(this._historySteps[pos]);
                this.historyStep(true);
                this.dispatchEvent(new Event('historyRedo'));
            }
        }
        /**
         * Check wether undoing is possible.
         */
        historyCanUndo() {
            return this._getNextUndoIndex() >= 0;
        }
        /**
         * Check wether redoing is possible.
         */
        historyCanRedo() {
            return this._getNextRedoIndex() >= 0;
        }
        historySize() {
            return this._historySteps.length;
        }

        historyRevert(step, until = 0) {
            // apply dom changes by reverting history steps
            for (let i = step.mutations.length - 1; i >= until; i--) {
                const mutation = step.mutations[i];
                if (!mutation) {
                    break;
                }
                switch (mutation.type) {
                    case 'characterData': {
                        const node = this.idFind(mutation.id);
                        if (node) node.textContent = mutation.oldValue;
                        break;
                    }
                    case 'attributes': {
                        const node = this.idFind(mutation.id);
                        if (node) {
                            if (mutation.oldValue) {
                                node.setAttribute(mutation.attributeName, mutation.oldValue);
                            } else {
                                node.removeAttribute(mutation.attributeName);
                            }
                        }
                        break;
                    }
                    case 'remove': {
                        const nodeToRemove = this.unserialize(mutation.node);
                        if (mutation.nextId && this.idFind(mutation.nextId)) {
                            const node = this.idFind(mutation.nextId);
                            node && node.before(nodeToRemove);
                        } else if (mutation.previousId && this.idFind(mutation.previousId)) {
                            const node = this.idFind(mutation.previousId);
                            node && node.after(nodeToRemove);
                        } else {
                            const node = this.idFind(mutation.parentId);
                            node && node.append(nodeToRemove);
                        }
                        break;
                    }
                    case 'add': {
                        const node = this.idFind(mutation.id);
                        if (node) {
                            node.remove();
                        }
                    }
                }
            }
            this._activateContenteditable();
            this.historySetCursor(step);
            this.dispatchEvent(new Event('historyRevert'));
        }

        /**
         * Place the cursor on the last known cursor position from the history steps.
         *
         * @returns {boolean}
         */
        resetCursorOnLastHistoryCursor() {
            const lastHistoryStep = this._historySteps[this._historySteps.length - 1];
            if (lastHistoryStep && lastHistoryStep.cursor && lastHistoryStep.cursor.anchorNode) {
                this.historySetCursor(lastHistoryStep);
                return true;
            }
            return false;
        }

        historySetCursor(step) {
            if (step.cursor && step.cursor.anchorNode) {
                const anchorNode = this.idFind(step.cursor.anchorNode);
                const focusNode = step.cursor.focusNode
                    ? this.idFind(step.cursor.focusNode)
                    : anchorNode;
                if (anchorNode) {
                    setCursor(
                        anchorNode,
                        step.cursor.anchorOffset,
                        focusNode,
                        step.cursor.focusOffset !== undefined
                            ? step.cursor.focusOffset
                            : step.cursor.anchorOffset,
                        false,
                    );
                }
            }
        }
        unbreakableStepUnactive() {
            this._toRollback =
                this._toRollback === UNBREAKABLE_ROLLBACK_CODE ? false : this._toRollback;
            this._checkStepUnbreakable = false;
        }

        /**
         * Same as @see _applyCommand, except that also simulates all the
         * contenteditable behaviors we let happen, e.g. the backspace handling
         * we then rollback.
         *
         * TODO this uses document.execCommand (which is deprecated) and relies on
         * the fact that using a command through it leads to the same result as
         * executing that command through a user keyboard on the unaltered editable
         * section with standard contenteditable attribute. This is already a huge
         * assomption.
         *
         * @param {string} method
         * @returns {?}
         */
        execCommand(...args) {
            this._computeHistoryCursor();
            return this._applyCommand(...args);
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _removeDomListener() {
            for (const [element, eventName, boundCallback] of this._domListeners) {
                element.removeEventListener(eventName, boundCallback);
            }
            this._domListeners = [];
        }

        // EDITOR COMMANDS
        // ===============

        deleteRange(sel) {
            let range = getDeepRange(this.editable, {
                sel,
                splitText: true,
                select: true,
                correctTripleClick: true,
            });
            if (!range) return;
            let start = range.startContainer;
            let end = range.endContainer;
            // Let the DOM split and delete the range.
            const doJoin = closestBlock(start) !== closestBlock(range.commonAncestorContainer);
            let next = nextLeaf(end, this.editable);
            const splitEndTd = closestElement(end, 'td') && end.nextSibling;
            const contents = range.extractContents();
            setCursor(start, nodeSize(start));
            range = getDeepRange(this.editable, { sel });
            // Restore unremovables removed by extractContents.
            [...contents.querySelectorAll('*')].filter(isUnremovable).forEach(n => {
                closestBlock(range.endContainer).after(n);
                n.textContent = '';
            });
            // Restore table contents removed by extractContents.
            const tds = [...contents.querySelectorAll('td')].filter(n => !closestElement(n, 'table'));
            let currentFragmentTr, currentTr;
            const currentTd = closestElement(range.endContainer, 'td');
            tds.forEach((td, i) => {
                const parentFragmentTr = closestElement(td, 'tr');
                // Skip the first and the last partially selected TD.
                if (i && !(splitEndTd && i === tds.length - 1)) {
                    if (parentFragmentTr !== currentFragmentTr) {
                        currentTr = currentTr
                            ? currentTr.nextElementSibling
                            : closestElement(range.endContainer, 'tr').nextElementSibling;
                    }
                    currentTr ? currentTr.prepend(td) : currentTd.after(td);
                }
                currentFragmentTr = parentFragmentTr;
                td.textContent = '';
            });
            this.observerFlush();
            this._toRollback = false; // Errors caught with observerFlush were already handled.
            // If the end container was fully selected, extractContents may have
            // emptied it without removing it. Ensure it's gone.
            const isRemovableInvisible = (node, noBlocks = true) =>
                !isVisible(node, noBlocks) && !isUnremovable(node) && node.nodeName !== 'A';
            const endIsStart = end === start;
            while (end && isRemovableInvisible(end, false) && !end.contains(range.endContainer)) {
                const parent = end.parentNode;
                end.remove();
                end = parent;
            }
            // Same with the start container
            while (
                start &&
                isRemovableInvisible(start) &&
                !(endIsStart && start.contains(range.startContainer))
            ) {
                const parent = start.parentNode;
                start.remove();
                start = parent;
            }
            // Ensure empty blocks be given a <br> child.
            if (start) {
                fillEmpty(closestBlock(start));
            }
            fillEmpty(closestBlock(range.endContainer));
            // Ensure trailing space remains visible.
            const joinWith = range.endContainer;
            const oldText = joinWith.textContent;
            if (joinWith && oldText.endsWith(' ')) {
                joinWith.textContent = oldText.replace(/ $/, '\u00A0');
                setCursor(joinWith, nodeSize(joinWith));
            }
            // Rejoin blocks that extractContents may have split in two.
            while (
                doJoin &&
                next &&
                !(next.previousSibling && next.previousSibling === joinWith) &&
                this.editable.contains(next)
            ) {
                const restore = preserveCursor(this.document);
                this.observerFlush();
                const res = this._protect(() => {
                    next.oDeleteBackward();
                    if (!this.editable.contains(joinWith)) {
                        this._toRollback = UNREMOVABLE_ROLLBACK_CODE; // tried to delete too far -> roll it back.
                    } else {
                        next = firstLeaf(next);
                    }
                }, this._historySteps[this._historySteps.length - 1].mutations.length);
                if ([UNBREAKABLE_ROLLBACK_CODE, UNREMOVABLE_ROLLBACK_CODE].includes(res)) {
                    restore();
                    break;
                }
            }
            next = joinWith && joinWith.nextSibling;
            if (
                joinWith &&
                oldText.endsWith(' ') &&
                !(next && next.nodeType === Node.TEXT_NODE && next.textContent.startsWith(' '))
            ) {
                // Restore the text we modified in order to preserve trailing space.
                joinWith.textContent = oldText;
                setCursor(joinWith, nodeSize(joinWith));
            }
        }

        updateColorpickerLabels(params = {}) {
            const foreColor = params.foreColor || rgbToHex(document.queryCommandValue('foreColor'));
            this.toolbar.style.setProperty('--fore-color', foreColor);
            const foreColorInput = this.toolbar.querySelector('#foreColor input');
            if (foreColorInput) {
                foreColorInput.value = foreColor;
            }

            let hiliteColor = params.hiliteColor;
            if (!hiliteColor) {
                const sel = this.document.getSelection();
                if (sel.rangeCount) {
                    const endContainer = closestElement(sel.getRangeAt(0).endContainer);
                    const hiliteColorRgb = getComputedStyle(endContainer).backgroundColor;
                    hiliteColor = rgbToHex(hiliteColorRgb);
                }
            }
            this.toolbar.style.setProperty('--hilite-color', hiliteColor);
            const hiliteColorInput = this.toolbar.querySelector('#hiliteColor input');
            if (hiliteColorInput) {
                hiliteColorInput.value = hiliteColor.length <= 7 ? hiliteColor : rgbToHex(hiliteColor);
            }
        }

        /**
         * Applies the given command to the current selection. This does *NOT*:
         * 1) update the history cursor
         * 2) protect the unbreakables or unremovables
         * 3) sanitize the result
         * 4) create new history entry
         * 5) follow the exact same operations that would be done following events
         *    that would lead to that command
         *
         * For points 1 -> 4, @see _applyCommand
         * For points 1 -> 5, @see execCommand
         *
         * @private
         * @param {string} method
         * @returns {?}
         */
        _applyRawCommand(method, ...args) {
            const sel = this.document.getSelection();
            if (!sel.isCollapsed && BACKSPACE_FIRST_COMMANDS.includes(method)) {
                this.deleteRange(sel);
                if (BACKSPACE_ONLY_COMMANDS.includes(method)) {
                    return true;
                }
            }
            if (editorCommands[method]) {
                return editorCommands[method](this, ...args);
            }
            if (method.startsWith('justify')) {
                const mode = method.split('justify').join('').toLocaleLowerCase();
                return this._align(mode === 'full' ? 'justify' : mode);
            }
            return sel.anchorNode[method](sel.anchorOffset, ...args);
        }

        /**
         * Same as @see _applyRawCommand but adapt history, protects unbreakables
         * and removables and sanitizes the result.
         *
         * @private
         * @param {string} method
         * @returns {?}
         */
        _applyCommand(...args) {
            this._recordHistoryCursor(true);
            const result = this._protect(() => this._applyRawCommand(...args));
            this.sanitize();
            this.historyStep();
            return result;
        }
        /**
         * @private
         * @param {function} callback
         * @param {number} [rollbackCounter]
         * @returns {?}
         */
        _protect(callback, rollbackCounter) {
            try {
                const result = callback.call(this);
                this.observerFlush();
                if (this._toRollback) {
                    const torollbackCode = this._toRollback;
                    this.historyRollback(rollbackCounter);
                    return torollbackCode; // UNBREAKABLE_ROLLBACK_CODE || UNREMOVABLE_ROLLBACK_CODE
                } else {
                    return result;
                }
            } catch (error) {
                if (error === UNBREAKABLE_ROLLBACK_CODE || error === UNREMOVABLE_ROLLBACK_CODE) {
                    this.historyRollback(rollbackCounter);
                    return error;
                } else {
                    throw error;
                }
            }
        }

        _activateContenteditable() {
            this.editable.setAttribute('contenteditable', this.options.isRootEditable);

            for (const node of this.options.getContentEditableAreas()) {
                if (!node.isContentEditable) {
                    node.setAttribute('contenteditable', true);
                }
            }
        }
        _stopContenteditable() {
            if (this.options.isRootEditable) {
                this.editable.setAttribute('contenteditable', !this.options.isRootEditable);
            }
            for (const node of this.options.getContentEditableAreas()) {
                if (node.getAttribute('contenteditable') === 'true') {
                    node.setAttribute('contenteditable', false);
                }
            }
        }

        // HISTORY
        // =======

        /**
         * @private
         * @returns {Object}
         */
        _computeHistoryCursor() {
            const sel = this.document.getSelection();
            if (!sel.anchorNode) {
                return this._latestComputedCursor;
            }
            this._latestComputedCursor = {
                anchorNode: sel.anchorNode.oid,
                anchorOffset: sel.anchorOffset,
                focusNode: sel.focusNode.oid,
                focusOffset: sel.focusOffset,
            };
            return this._latestComputedCursor;
        }
        /**
         * @private
         * @param {boolean} [useCache=false]
         */
        _recordHistoryCursor(useCache = false) {
            const latest = this._historySteps[this._historySteps.length - 1];
            latest.cursor =
                (useCache ? this._latestComputedCursor : this._computeHistoryCursor()) || {};
        }
        /**
         * Get the step index in the history to undo.
         * Return -1 if no undo index can be found.
         */
        _getNextUndoIndex() {
            let index = this._historySteps.length - 2;
            // go back to first step that can be undoed (0 or undefined)
            while (this._historyStepsStates.get(index)) {
                index--;
            }
            return index;
        }
        /**
         * Get the step index in the history to redo.
         * Return -1 if no redo index can be found.
         */
        _getNextRedoIndex() {
            let pos = this._historySteps.length - 2;
            // We cannot redo more than what is consumed.
            // Check if we have no more 2 than 0 until we get to a 1
            let totalConsumed = 0;
            while (this._historyStepsStates.has(pos) && this._historyStepsStates.get(pos) !== 1) {
                // here ._historyStepsState.get(pos) can only be 2 (consumed) or 0 (undoed).
                totalConsumed += this._historyStepsStates.get(pos) === 2 ? 1 : -1;
                pos--;
            }
            const canRedo = this._historyStepsStates.get(pos) === 1 && totalConsumed <= 0;
            return canRedo ? pos : -1;
        }

        // TOOLBAR
        // =======

        /**
         * @private
         * @param {boolean} [show]
         */
        _updateToolbar(show) {
            if (!this.options.toolbar) return;
            if (!this.options.autohideToolbar && this.toolbar.style.visibility !== 'visible') {
                this.toolbar.style.visibility = 'visible';
            }

            const sel = this.document.getSelection();
            if (!sel.anchorNode) {
                show = false;
            }
            if (this.options.autohideToolbar) {
                if (show !== undefined && !this.isMobile) {
                    this.toolbar.style.visibility = show ? 'visible' : 'hidden';
                }
                if (show === false) {
                    return;
                }
            }
            const paragraphDropdownButton = this.toolbar.querySelector('#paragraphDropdownButton');
            for (const commandState of [
                'italic',
                'underline',
                'strikeThrough',
                'justifyLeft',
                'justifyRight',
                'justifyCenter',
                'justifyFull',
            ]) {
                const isStateTrue = this.document.queryCommandState(commandState);
                const button = this.toolbar.querySelector('#' + commandState);
                if (commandState.startsWith('justify')) {
                    if (paragraphDropdownButton) {
                        button.classList.toggle('active', isStateTrue);
                        const direction = commandState.replace('justify', '').toLowerCase();
                        const newClass = `fa-align-${direction === 'full' ? 'justify' : direction}`;
                        paragraphDropdownButton.classList.toggle(newClass, isStateTrue);
                    }
                } else if (button) {
                    button.classList.toggle('active', isStateTrue);
                }
            }
            if (sel.rangeCount) {
                const closestsStartContainer = closestElement(sel.getRangeAt(0).startContainer, '*');
                const selectionStartStyle = getComputedStyle(closestsStartContainer);

                // queryCommandState('bold') does not take stylesheets into account
                const isBold = Number.parseInt(selectionStartStyle.fontWeight) > 500;
                const button = this.toolbar.querySelector('#bold');
                button.classList.toggle('active', isBold);

                const fontSizeValue = this.toolbar.querySelector('#fontSizeCurrentValue');
                if (fontSizeValue) {
                    fontSizeValue.textContent = /\d+/.exec(selectionStartStyle.fontSize).pop();
                }
                const table = getInSelection(this.document, 'table');
                const toolbarButton = this.toolbar.querySelector('.toolbar-edit-table');
                if (toolbarButton) {
                    this.toolbar.querySelector('.toolbar-edit-table').style.display = table
                        ? 'block'
                        : 'none';
                }
            }
            this.updateColorpickerLabels();
            const block = closestBlock(sel.anchorNode);
            for (const [style, tag, isList] of [
                ['paragraph', 'P', false],
                ['heading1', 'H1', false],
                ['heading2', 'H2', false],
                ['heading3', 'H3', false],
                ['blockquote', 'BLOCKQUOTE', false],
                ['unordered', 'UL', true],
                ['ordered', 'OL', true],
                ['checklist', 'CL', true],
            ]) {
                const button = this.toolbar.querySelector('#' + style);
                if (button && !block) {
                    button.classList.toggle('active', false);
                } else if (button) {
                    const isActive = isList
                        ? block.tagName === 'LI' && getListMode(block.parentElement) === tag
                        : block.tagName === tag;
                    button.classList.toggle('active', isActive);
                }
            }
            const linkNode = getInSelection(this.document, 'a');
            const linkButton = this.toolbar.querySelector('#createLink');
            linkButton && linkButton.classList.toggle('active', linkNode);
            const unlinkButton = this.toolbar.querySelector('#unlink');
            unlinkButton && unlinkButton.classList.toggle('d-none', !linkNode);
            const undoButton = this.toolbar.querySelector('#undo');
            undoButton && undoButton.classList.toggle('disabled', !this.historyCanUndo());
            const redoButton = this.toolbar.querySelector('#redo');
            redoButton && redoButton.classList.toggle('disabled', !this.historyCanRedo());
            if (this.options.autohideToolbar && !this.isMobile) {
                this._positionToolbar();
            }
        }
        _positionToolbar() {
            const OFFSET = 10;
            let isBottom = false;
            this.toolbar.classList.toggle('toolbar-bottom', false);
            this.toolbar.style.maxWidth = this.editable.offsetWidth - OFFSET * 2 + 'px';
            const sel = this.document.getSelection();
            const range = sel.getRangeAt(0);
            const isSelForward =
                sel.anchorNode === range.startContainer && sel.anchorOffset === range.startOffset;
            const selRect = range.getBoundingClientRect();
            const toolbarWidth = this.toolbar.offsetWidth;
            const toolbarHeight = this.toolbar.offsetHeight;
            const editorRect = this.editable.getBoundingClientRect();
            const parentContextRect = this.options.getContextFromParentRect();
            const editorLeftPos = Math.max(0, editorRect.left);
            const editorTopPos = Math.max(0, editorRect.top);
            const scrollX = this.document.defaultView.scrollX;
            const scrollY = this.document.defaultView.scrollY;

            // Get left position.
            let left = selRect.left + OFFSET;
            // Ensure the toolbar doesn't overflow the editor on the left.
            left = Math.max(editorLeftPos + OFFSET, left);
            // Ensure the toolbar doesn't overflow the editor on the right.
            left = Math.min(editorLeftPos + this.editable.offsetWidth - OFFSET - toolbarWidth, left);
            // Offset left to compensate for parent context position (eg. Iframe).
            left += parentContextRect.left;
            this.toolbar.style.left = scrollX + left + 'px';

            // Get top position.
            let top = selRect.top - toolbarHeight - OFFSET;
            // Ensure the toolbar doesn't overflow the editor on the top.
            if (top < editorTopPos) {
                // Position the toolbar below the selection.
                top = selRect.bottom + OFFSET;
                isBottom = true;
            }
            // Ensure the toolbar doesn't overflow the editor on the bottom.
            top = Math.min(editorTopPos + this.editable.offsetHeight - OFFSET - toolbarHeight, top);
            // Offset top to compensate for parent context position (eg. Iframe).
            top += parentContextRect.top;
            this.toolbar.style.top = scrollY + top + 'px';

            // Position the arrow.
            let arrowLeftPos = (isSelForward ? selRect.right : selRect.left) - left - OFFSET;
            // Ensure the arrow doesn't overflow the toolbar on the left.
            arrowLeftPos = Math.max(OFFSET, arrowLeftPos);
            // Ensure the arrow doesn't overflow the toolbar on the right.
            arrowLeftPos = Math.min(toolbarWidth - OFFSET - 20, arrowLeftPos);
            this.toolbar.style.setProperty('--arrow-left-pos', arrowLeftPos + 'px');
            if (isBottom) {
                this.toolbar.classList.toggle('toolbar-bottom', true);
                this.toolbar.style.setProperty('--arrow-top-pos', -17 + 'px');
            } else {
                this.toolbar.style.setProperty('--arrow-top-pos', toolbarHeight - 3 + 'px');
            }
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * If backspace/delete input, rollback the operation and handle the
         * operation ourself. Needed for mobile, used for desktop for consistency.
         *
         * @private
         */
        _onInput(ev) {
            // Record the cursor position that was computed on keydown or before
            // contentEditable execCommand (whatever preceded the 'input' event)
            this._recordHistoryCursor(true);
            const cursor = this._historySteps[this._historySteps.length - 1].cursor;
            const { focusOffset, focusNode, anchorNode, anchorOffset } = cursor || {};
            const wasCollapsed = !cursor || (focusNode === anchorNode && focusOffset === anchorOffset);
            if (this.keyboardType === KEYBOARD_TYPES.PHYSICAL || !wasCollapsed) {
                if (ev.inputType === 'deleteContentBackward') {
                    this.historyRollback();
                    ev.preventDefault();
                    this._applyCommand('oDeleteBackward');
                } else if (ev.inputType === 'deleteContentForward') {
                    this.historyRollback();
                    ev.preventDefault();
                    this._applyCommand('oDeleteForward');
                } else if (
                    ev.inputType === 'insertParagraph' ||
                    (ev.inputType === 'insertText' && ev.data === null)
                ) {
                    // Sometimes the browser wrongly triggers an insertText
                    // input event with null data on enter.
                    this.historyRollback();
                    ev.preventDefault();
                    if (this._applyCommand('oEnter') === UNBREAKABLE_ROLLBACK_CODE) {
                        this._applyCommand('oShiftEnter');
                    }
                } else if (['insertText', 'insertCompositionText'].includes(ev.inputType)) {
                    // insertCompositionText, courtesy of Samsung keyboard.
                    const selection = this.document.getSelection();
                    // Detect that text was selected and change behavior only if it is the case,
                    // since it is the only text insertion case that may cause problems.
                    if (anchorNode !== focusNode || anchorOffset !== focusOffset) {
                        ev.preventDefault();
                        this._applyRawCommand('oDeleteBackward');
                        insertText(selection, ev.data);
                        const range = selection.getRangeAt(0);
                        setCursor(range.endContainer, range.endOffset);
                    }
                    this.sanitize();
                    this.historyStep();
                } else if (ev.inputType === 'insertLineBreak') {
                    this.historyRollback();
                    ev.preventDefault();
                    this._applyCommand('oShiftEnter');
                } else {
                    this.sanitize();
                    this.historyStep();
                }
            }
        }

        /**
         * @private
         */
        _onKeyDown(ev) {
            this.keyboardType =
                ev.key === 'Unidentified' ? KEYBOARD_TYPES.VIRTUAL : KEYBOARD_TYPES.PHYSICAL;
            // If the pressed key has a printed representation, the returned value
            // is a non-empty Unicode character string containing the printable
            // representation of the key. In this case, call `deleteRange` before
            // inserting the printed representation of the character.
            if (/^.$/u.test(ev.key) && !ev.ctrlKey && !ev.metaKey) {
                const selection = this.document.getSelection();
                if (selection && !selection.isCollapsed) {
                    this.deleteRange(selection);
                }
            }
            if (ev.key === 'Backspace' && !ev.ctrlKey && !ev.metaKey) {
                // backspace
                // We need to hijack it because firefox doesn't trigger a
                // deleteBackward input event with a collapsed cursor in front of a
                // contentEditable="false" (eg: font awesome)
                const selection = this.document.getSelection();
                if (selection.isCollapsed) {
                    ev.preventDefault();
                    this._applyCommand('oDeleteBackward');
                }
            } else if (ev.key === 'Tab') {
                // Tab
                const sel = this.document.getSelection();
                const closestTag = (closestElement(sel.anchorNode, 'li, table') || {}).tagName;

                if (closestTag === 'LI') {
                    this._applyCommand('indentList', ev.shiftKey ? 'outdent' : 'indent');
                    ev.preventDefault();
                } else if (closestTag === 'TABLE') {
                    this._onTabulationInTable(ev);
                    ev.preventDefault();
                }
            } else if (isUndo(ev)) {
                // Ctrl-Z
                ev.preventDefault();
                ev.stopPropagation();
                this.historyUndo();
            } else if (isRedo(ev)) {
                // Ctrl-Y
                ev.preventDefault();
                ev.stopPropagation();
                this.historyRedo();
            }
        }
        /**
         * @private
         */
        _onSelectionChange() {
            // Compute the current cursor on selectionchange but do not record it. Leave
            // that to the command execution or the 'input' event handler.
            this._computeHistoryCursor();

            const selection = this.document.getSelection();
            const isSelectionInEditable =
                !selection.isCollapsed &&
                this.editable.contains(selection.anchorNode) &&
                this.editable.contains(selection.focusNode);
            this._updateToolbar(isSelectionInEditable);

            if (this._currentMouseState === 'mouseup') {
                this._fixFontAwesomeSelection();
            }

            // When the browser set the selection inside a node that is
            // contenteditable=false, it breaks the edition upon keystroke. Move the
            // selection so that it remain in an editable area. An example of this
            // case happend when the selection goes into a fontawesome node.
            const startContainer =
                selection.rangeCount && closestElement(selection.getRangeAt(0).startContainer);
            const contenteditableFalseNode =
                startContainer &&
                !startContainer.isContentEditable &&
                ancestors(startContainer, this.editable).includes(this.editable) &&
                startContainer.closest('[contenteditable=false]');
            if (contenteditableFalseNode) {
                selection.removeAllRanges();
                const range = new Range();
                if (contenteditableFalseNode.previousSibling) {
                    range.setStart(
                        contenteditableFalseNode.previousSibling,
                        contenteditableFalseNode.previousSibling.length,
                    );
                    range.setEnd(
                        contenteditableFalseNode.previousSibling,
                        contenteditableFalseNode.previousSibling.length,
                    );
                } else {
                    range.setStart(contenteditableFalseNode.parentElement, 0);
                    range.setEnd(contenteditableFalseNode.parentElement, 0);
                }
                selection.addRange(range);
            }
        }

        _onMouseup(ev) {
            this._currentMouseState = ev.type;

            this._fixFontAwesomeSelection();
        }

        _onMouseDown(ev) {
            this._currentMouseState = ev.type;

            // When selecting all the text within a link then triggering delete or
            // inserting a character, the cursor and insertion is outside the link.
            // To avoid this problem, we make all editable zone become uneditable
            // except the link. Then when cliking outside the link, reset the
            // editable zones.
            this.automaticStepSkipStack();
            const link = closestElement(ev.target, 'a');
            if (link && !link.querySelector('div') && !closestElement(ev.target, '.o_not_editable')) {
                const editableChildren = link.querySelectorAll('[contenteditable=true]');
                this._stopContenteditable();
                [...editableChildren, link].forEach(node => node.setAttribute('contenteditable', true));
            } else {
                this._activateContenteditable();
            }

            const node = ev.target;
            // handle checkbox lists
            if (node.tagName == 'LI' && getListMode(node.parentElement) == 'CL') {
                if (ev.offsetX < 0) {
                    toggleClass(node, 'o_checked');
                    ev.preventDefault();
                }
            }
        }

        _onDocumentKeydown(ev) {
            const canUndoRedo = !['INPUT', 'TEXTAREA'].includes(this.document.activeElement.tagName);

            if (this.options.controlHistoryFromDocument && canUndoRedo) {
                if (isUndo(ev) && canUndoRedo) {
                    ev.preventDefault();
                    this.historyUndo();
                } else if (isRedo(ev) && canUndoRedo) {
                    ev.preventDefault();
                    this.historyRedo();
                }
            } else {
                if (isRedo(ev) || isUndo(ev)) {
                    this._onKeyupResetContenteditableNodes.push(
                        ...this.editable.querySelectorAll('[contenteditable=true]'),
                    );
                    if (this.editable.getAttribute('contenteditable') === 'true') {
                        this._onKeyupResetContenteditableNodes.push(this.editable);
                    }

                    for (const node of this._onKeyupResetContenteditableNodes) {
                        this.automaticStepSkipStack();
                        node.setAttribute('contenteditable', false);
                    }
                }
            }
        }

        _onDocumentKeyup() {
            if (this._onKeyupResetContenteditableNodes.length) {
                for (const node of this._onKeyupResetContenteditableNodes) {
                    this.automaticStepSkipStack();
                    node.setAttribute('contenteditable', true);
                }
                this._onKeyupResetContenteditableNodes = [];
            }
        }

        /**
         * Prevent the pasting of HTML and paste text only instead.
         */
        _onPaste(ev) {
            ev.preventDefault();
            const pastedText = (ev.originalEvent || ev).clipboardData.getData('text/plain');
            this.execCommand('insertText', pastedText);
        }

        /**
         * Prevent the dropping of HTML and paste text only instead.
         */
        _onDrop(ev) {
            ev.preventDefault();
            const sel = this.document.getSelection();
            let isInEditor = false;
            let ancestor = sel.anchorNode;
            while (ancestor && !isInEditor) {
                if (ancestor === this.editable) {
                    isInEditor = true;
                }
                ancestor = ancestor.parentNode;
            }
            const transferItem = [...(ev.originalEvent || ev).dataTransfer.items].find(
                item => item.type === 'text/plain',
            );
            if (transferItem) {
                transferItem.getAsString(pastedText => {
                    if (isInEditor && !sel.isCollapsed) {
                        this.deleteRange(sel);
                    }
                    if (document.caretPositionFromPoint) {
                        const range = this.document.caretPositionFromPoint(ev.clientX, ev.clientY);
                        setCursor(range.offsetNode, range.offset);
                    } else if (document.caretRangeFromPoint) {
                        const range = this.document.caretRangeFromPoint(ev.clientX, ev.clientY);
                        setCursor(range.startContainer, range.startOffset);
                    }
                    insertText(this.document.getSelection(), pastedText);
                });
            }
            this.historyStep();
        }

        _bindToolbar() {
            for (const buttonEl of this.toolbar.querySelectorAll('[data-call]')) {
                buttonEl.addEventListener('mousedown', ev => {
                    this.execCommand(buttonEl.dataset.call, buttonEl.dataset.arg1);

                    ev.preventDefault();
                    this._updateToolbar();
                });
            }
        }
        _initTablePicker() {
            for (const child of [...this.tablePicker.childNodes]) {
                child.remove();
            }
            this.tablePicker.dataset.rowCount = 0;
            this.tablePicker.dataset.colCount = 0;
            for (let rowIndex = 0; rowIndex < TABLEPICKER_ROW_COUNT; rowIndex++) {
                this._addTablePickerRow();
            }
            for (let colIndex = 0; colIndex < TABLEPICKER_COL_COUNT; colIndex++) {
                this._addTablePickerColumn();
            }
            this.tablePicker.querySelector('.tablepicker-cell').classList.toggle('active', true);
            this.tablePickerSizeView.textContent = '1x1';
        }
        _addTablePickerRow() {
            const row = this.document.createElement('div');
            row.classList.add('tablepicker-row');
            row.dataset.rowId = this.tablePicker.querySelectorAll('.tablepicker-row').length + 1;
            this.tablePicker.appendChild(row);
            this.tablePicker.dataset.rowCount = +this.tablePicker.dataset.rowCount + 1;
            for (let i = 0; i < +this.tablePicker.dataset.colCount; i++) {
                this._addTablePickerCell(row);
            }
            return row;
        }
        _addTablePickerColumn() {
            for (const row of this.tablePicker.querySelectorAll('.tablepicker-row')) {
                this._addTablePickerCell(row);
            }
            this.tablePicker.dataset.colCount = +this.tablePicker.dataset.colCount + 1;
        }
        _addTablePickerCell(row) {
            const rowId = +row.dataset.rowId;
            const colId = row.querySelectorAll('.tablepicker-cell').length + 1;
            const cell = this.document.createElement('div');
            cell.classList.add('tablepicker-cell', 'btn');
            cell.dataset.rowId = rowId;
            cell.dataset.colId = colId;
            row.appendChild(cell);
            cell.addEventListener('mouseover', () => this._onHoverTablePickerCell(rowId, colId));
        }
        _onHoverTablePickerCell(targetRowId, targetColId) {
            // Hightlight the active cells, remove highlight of the others.
            for (const cell of this.tablePicker.querySelectorAll('.tablepicker-cell')) {
                const [rowId, colId] = [+cell.dataset.rowId, +cell.dataset.colId];
                const isActive = rowId <= targetRowId && colId <= targetColId;
                cell.classList.toggle('active', isActive);
            }
            this.tablePickerSizeView.textContent = `${targetColId}x${targetRowId}`;

            // Add/remove rows to expand/shrink the tablepicker.
            if (targetRowId >= +this.tablePicker.dataset.rowCount) {
                this._addTablePickerRow();
            } else if (+this.tablePicker.dataset.rowCount > TABLEPICKER_ROW_COUNT) {
                for (const row of this.tablePicker.querySelectorAll('.tablepicker-row')) {
                    const rowId = +row.dataset.rowId;
                    if (rowId >= TABLEPICKER_ROW_COUNT && rowId > targetRowId + 1) {
                        row.remove();
                        this.tablePicker.dataset.rowCount = +this.tablePicker.dataset.rowCount - 1;
                    }
                }
            }
            // Add/remove cols to expand/shrink the tablepicker.
            const colCount = +this.tablePicker.dataset.colCount;
            if (targetColId >= colCount) {
                this._addTablePickerColumn();
            } else if (colCount > TABLEPICKER_COL_COUNT) {
                const removedColIds = new Set();
                for (const cell of this.tablePicker.querySelectorAll('.tablepicker-cell')) {
                    const colId = +cell.dataset.colId;
                    if (colId >= TABLEPICKER_COL_COUNT && colId > targetColId + 1) {
                        cell.remove();
                        removedColIds.add(colId);
                    }
                }
                this.tablePicker.dataset.colCount = colCount - removedColIds.size;
            }
        }
        _onTabulationInTable(ev) {
            const sel = this.document.getSelection();
            const closestTable = closestElement(sel.anchorNode, 'table');
            if (!closestTable) {
                return;
            }
            const closestTd = closestElement(sel.anchorNode, 'td');
            const tds = [...closestTable.querySelectorAll('td')];
            const direction = ev.shiftKey ? DIRECTIONS.LEFT : DIRECTIONS.RIGHT;
            const cursorDestination =
                tds[tds.findIndex(td => closestTd === td) + (direction === DIRECTIONS.LEFT ? -1 : 1)];
            if (cursorDestination) {
                setCursor(...startPos(cursorDestination), ...endPos(cursorDestination), true);
            } else if (direction === DIRECTIONS.RIGHT) {
                this._addRowBelow();
                this._onTabulationInTable(ev);
            }
        }

        /**
         * Fix the current selection range in case the range start or end inside a fontAwesome node
         */
        _fixFontAwesomeSelection() {
            const selection = this.document.getSelection();
            if (
                selection.isCollapsed ||
                (selection.anchorNode &&
                    !ancestors(selection.anchorNode, this.editable).includes(this.editable))
            )
                return;
            let shouldUpdateSelection = false;
            const fixedSelection = {
                anchorNode: selection.anchorNode,
                anchorOffset: selection.anchorOffset,
                focusNode: selection.focusNode,
                focusOffset: selection.focusOffset,
            };
            const selectionDirection = getCursorDirection(
                selection.anchorNode,
                selection.anchorOffset,
                selection.focusNode,
                selection.focusOffset,
            );
            // check and fix anchor node
            const closestAnchorNodeEl = closestElement(selection.anchorNode);
            if (isFontAwesome(closestAnchorNodeEl)) {
                shouldUpdateSelection = true;
                fixedSelection.anchorNode =
                    selectionDirection === DIRECTIONS.RIGHT
                        ? closestAnchorNodeEl.previousSibling
                        : closestAnchorNodeEl.nextSibling;
                if (fixedSelection.anchorNode) {
                    fixedSelection.anchorOffset =
                        selectionDirection === DIRECTIONS.RIGHT ? fixedSelection.anchorNode.length : 0;
                } else {
                    fixedSelection.anchorNode = closestAnchorNodeEl.parentElement;
                    fixedSelection.anchorOffset = 0;
                }
            }
            // check and fix focus node
            const closestFocusNodeEl = closestElement(selection.focusNode);
            if (isFontAwesome(closestFocusNodeEl)) {
                shouldUpdateSelection = true;
                fixedSelection.focusNode =
                    selectionDirection === DIRECTIONS.RIGHT
                        ? closestFocusNodeEl.nextSibling
                        : closestFocusNodeEl.previousSibling;
                if (fixedSelection.focusNode) {
                    fixedSelection.focusOffset =
                        selectionDirection === DIRECTIONS.RIGHT ? 0 : fixedSelection.focusNode.length;
                } else {
                    fixedSelection.focusNode = closestFocusNodeEl.parentElement;
                    fixedSelection.focusOffset = 0;
                }
            }
            if (shouldUpdateSelection) {
                setCursor(
                    fixedSelection.anchorNode,
                    fixedSelection.anchorOffset,
                    fixedSelection.focusNode,
                    fixedSelection.focusOffset,
                    false,
                );
            }
        }
    }

    exports.BACKSPACE_FIRST_COMMANDS = BACKSPACE_FIRST_COMMANDS;
    exports.BACKSPACE_ONLY_COMMANDS = BACKSPACE_ONLY_COMMANDS;
    exports.CTGROUPS = CTGROUPS;
    exports.CTYPES = CTYPES;
    exports.DIRECTIONS = DIRECTIONS;
    exports.OdooEditor = OdooEditor;
    exports.UNBREAKABLE_ROLLBACK_CODE = UNBREAKABLE_ROLLBACK_CODE;
    exports.UNREMOVABLE_ROLLBACK_CODE = UNREMOVABLE_ROLLBACK_CODE;
    exports.ancestors = ancestors;
    exports.boundariesIn = boundariesIn;
    exports.boundariesOut = boundariesOut;
    exports.childNodeIndex = childNodeIndex;
    exports.clearEmpty = clearEmpty;
    exports.closestBlock = closestBlock;
    exports.closestElement = closestElement;
    exports.closestPath = closestPath;
    exports.commonParentGet = commonParentGet;
    exports.containsUnbreakable = containsUnbreakable;
    exports.containsUnremovable = containsUnremovable;
    exports.createDOMPathGenerator = createDOMPathGenerator;
    exports.createList = createList;
    exports.endPos = endPos;
    exports.enforceWhitespace = enforceWhitespace;
    exports.fillEmpty = fillEmpty;
    exports.findNode = findNode;
    exports.firstLeaf = firstLeaf;
    exports.getAdjacentNextSiblings = getAdjacentNextSiblings;
    exports.getAdjacentPreviousSiblings = getAdjacentPreviousSiblings;
    exports.getAdjacents = getAdjacents;
    exports.getCursorDirection = getCursorDirection;
    exports.getCursors = getCursors;
    exports.getDeepRange = getDeepRange;
    exports.getDeepestPosition = getDeepestPosition;
    exports.getInSelection = getInSelection;
    exports.getListMode = getListMode;
    exports.getNormalizedCursorPosition = getNormalizedCursorPosition;
    exports.getOuid = getOuid;
    exports.getSelectedNodes = getSelectedNodes;
    exports.getState = getState;
    exports.getTraversedNodes = getTraversedNodes;
    exports.insertListAfter = insertListAfter;
    exports.insertText = insertText;
    exports.isBlock = isBlock;
    exports.isContentTextNode = isContentTextNode;
    exports.isEmptyBlock = isEmptyBlock;
    exports.isFakeLineBreak = isFakeLineBreak;
    exports.isFontAwesome = isFontAwesome;
    exports.isInPre = isInPre;
    exports.isMediaElement = isMediaElement;
    exports.isShrunkBlock = isShrunkBlock;
    exports.isUnbreakable = isUnbreakable;
    exports.isUnremovable = isUnremovable;
    exports.isVisible = isVisible;
    exports.isVisibleEmpty = isVisibleEmpty;
    exports.isVisibleStr = isVisibleStr;
    exports.lastLeaf = lastLeaf;
    exports.leftDeepFirstInlinePath = leftDeepFirstInlinePath;
    exports.leftDeepFirstPath = leftDeepFirstPath;
    exports.leftDeepOnlyInlineInScopePath = leftDeepOnlyInlineInScopePath;
    exports.leftDeepOnlyInlinePath = leftDeepOnlyInlinePath;
    exports.leftDeepOnlyPath = leftDeepOnlyPath;
    exports.leftPos = leftPos;
    exports.moveNodes = moveNodes;
    exports.nextLeaf = nextLeaf;
    exports.nodeSize = nodeSize;
    exports.parentsGet = parentsGet;
    exports.prepareUpdate = prepareUpdate;
    exports.preserveCursor = preserveCursor;
    exports.previousLeaf = previousLeaf;
    exports.restoreState = restoreState;
    exports.rgbToHex = rgbToHex;
    exports.rightDeepFirstInlinePath = rightDeepFirstInlinePath;
    exports.rightDeepFirstPath = rightDeepFirstPath;
    exports.rightDeepOnlyInlineInScopePath = rightDeepOnlyInlineInScopePath;
    exports.rightDeepOnlyInlinePath = rightDeepOnlyInlinePath;
    exports.rightDeepOnlyPath = rightDeepOnlyPath;
    exports.rightPos = rightPos;
    exports.setCursor = setCursor;
    exports.setCursorEnd = setCursorEnd;
    exports.setCursorStart = setCursorStart;
    exports.setTagName = setTagName;
    exports.splitElement = splitElement;
    exports.splitTextNode = splitTextNode;
    exports.startPos = startPos;
    exports.toggleClass = toggleClass;

    Object.defineProperty(exports, '__esModule', { value: true });

    return exports;

}({}));
return exportVariable;
}));
