import { closestBlock } from "@html_editor/utils/blocks";
import {
    getDeepestPosition,
    isMediaElement,
    isProtected,
    isProtecting,
    isUnprotecting,
} from "@html_editor/utils/dom_info";
import {
    childNodes,
    closestElement,
    descendants,
    firstLeaf,
    lastLeaf,
} from "@html_editor/utils/dom_traversal";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Plugin } from "../plugin";
import { DIRECTIONS, leftPos, nodeSize, rightPos } from "../utils/position";
import {
    getAdjacentCharacter,
    normalizeDeepCursorPosition,
    normalizeFakeBR,
    normalizeNotEditableNode,
    normalizeSelfClosingElement,
} from "../utils/selection";
import { closestScrollableY } from "@web/core/utils/scrolling";

/**
 * @typedef { Object } EditorSelection
 * @property { Node } anchorNode
 * @property { number } anchorOffset
 * @property { Node } focusNode
 * @property { number } focusOffset
 * @property { Node } startContainer
 * @property { number } startOffset
 * @property { Node } endContainer
 * @property { number } endOffset
 * @property { Node } commonAncestorContainer
 * @property { boolean } isCollapsed
 * @property { boolean } direction
 * @property { () => string } textContent
 * @property { (node: Node) => boolean } intersectsNode
 */

/**
 * @typedef {Object} SelectionData
 * @property {EditorSelection} documentSelection
 * @property {EditorSelection} editableSelection
 * @property {EditorSelection} deepEditableSelection
 * @property { boolean } documentSelectionIsInEditable
 * @property { boolean } documentSelectionIsProtected
 * @property { boolean } documentSelectionIsProtecting
 */

/**
 * @typedef {Object} Cursors
 * @property {() => void} restore
 * @property {(callback: (cursor: Cursor) => void) => Cursors} update
 * @property {(node: Node, newNode: Node) => Cursors} remapNode
 * @property {(node: Node, newOffset: number) => Cursors} setOffset
 * @property {(node: Node, shiftOffset: number) => Cursors} shiftOffset
 */

/**
 * @typedef {Object} Cursor
 * @property {Node} node
 * @property {number} offset
 */

// https://developer.mozilla.org/en-US/docs/Glossary/Void_element
const VOID_ELEMENT_NAMES = [
    "AREA",
    "BASE",
    "BR",
    "COL",
    "EMBED",
    "HR",
    "IMG",
    "INPUT",
    "KEYGEN",
    "LINK",
    "META",
    "PARAM",
    "SOURCE",
    "TRACK",
    "WBR",
];

export function isArtificialVoidElement(node) {
    return isMediaElement(node) || node.nodeName === "HR";
}

export function isNotAllowedContent(node) {
    return isArtificialVoidElement(node) || VOID_ELEMENT_NAMES.includes(node.nodeName);
}

function getUnselectedEdgeNodes(selection) {
    const startEdgeNodes = (node, offset) =>
        node === selection.commonAncestorContainer || offset < nodeSize(node)
            ? []
            : [node, ...startEdgeNodes(...rightPos(node))];
    const endEdgeNodes = (node, offset) =>
        node === selection.commonAncestorContainer || offset > 0
            ? []
            : [node, ...endEdgeNodes(...leftPos(node))];
    return new Set([
        ...startEdgeNodes(selection.startContainer, selection.startOffset),
        ...endEdgeNodes(selection.endContainer, selection.endOffset),
    ]);
}

/**
 * Scrolls the view to a specific node's position in the document
 * @param {Selection} selection - The current document selection
 * @returns {void}
 */
function scrollToSelection(selection) {
    const range = selection.getRangeAt(0);
    const container = closestScrollableY(range.startContainer.parentElement);
    if (!container) {
        // If the container is not scrollable we don't scroll
        return;
    }
    let rect = range.getBoundingClientRect();
    // If the range is invisible (0 width & height),
    // We call `getBoundingClientRect` on closest element.
    if (rect.width === 0 && rect.height === 0 && selection.isCollapsed) {
        rect = closestElement(selection.anchorNode).getBoundingClientRect();
    }

    const containerRect = container.getBoundingClientRect();
    const offsetTop = rect.top - containerRect.top + container.scrollTop;
    const offsetBottom = rect.bottom - containerRect.top + container.scrollTop;

    if (rect.bottom > containerRect.top && rect.top < containerRect.bottom) {
        // If selection is partially visible, no need to scroll.
        return;
    }
    // Simulate the "nearest" behavior by scrolling to the closest top/bottom edge
    if (rect.top < containerRect.top) {
        container.scrollTo({ top: offsetTop, behavior: "instant" });
    } else if (rect.bottom > containerRect.bottom) {
        container.scrollTo({ top: offsetBottom - container.clientHeight, behavior: "instant" });
    }
}

/**
 * @typedef { Object } SelectionShared
 * @property { SelectionPlugin['extractContent'] } extractContent
 * @property { SelectionPlugin['focusEditable'] } focusEditable
 * @property { SelectionPlugin['getEditableSelection'] } getEditableSelection
 * @property { SelectionPlugin['getSelectedNodes'] } getSelectedNodes
 * @property { SelectionPlugin['getSelectionData'] } getSelectionData
 * @property { SelectionPlugin['getTraversedBlocks'] } getTraversedBlocks
 * @property { SelectionPlugin['getTraversedNodes'] } getTraversedNodes
 * @property { SelectionPlugin['getTargetedBlocks'] } getTargetedBlocks
 * @property { SelectionPlugin['getTargetedNodes'] } getTargetedNodes
 * @property { SelectionPlugin['modifySelection'] } modifySelection
 * @property { SelectionPlugin['preserveSelection'] } preserveSelection
 * @property { SelectionPlugin['rectifySelection'] } rectifySelection
 * @property { SelectionPlugin['isNodeContentsFullySelected'] } isNodeContentsFullySelected
 * @property { SelectionPlugin['areNodeContentsFullySelected'] } areNodeContentsFullySelected
 * @property { SelectionPlugin['resetActiveSelection'] } resetActiveSelection
 * @property { SelectionPlugin['resetSelection'] } resetSelection
 * @property { SelectionPlugin['setCursorEnd'] } setCursorEnd
 * @property { SelectionPlugin['setCursorStart'] } setCursorStart
 * @property { SelectionPlugin['setSelection'] } setSelection
 * @property { SelectionPlugin['selectAroundNonEditable'] } selectAroundNonEditable
 */

export class SelectionPlugin extends Plugin {
    static id = "selection";
    static shared = [
        "getSelectionData",
        "getEditableSelection",
        "setSelection",
        "setCursorStart",
        "setCursorEnd",
        "extractContent",
        "preserveSelection",
        "resetSelection",
        "getSelectedNodes", // Deprecated. Prefer `getTargetedNodes`.
        "getTraversedNodes", // Deprecated. Prefer `getTargetedNodes`.
        "getTraversedBlocks", // Deprecated. Prefer `getTargetedBlocks`.
        "getTargetedNodes",
        "getTargetedBlocks",
        "modifySelection",
        "rectifySelection",
        "isNodeContentsFullySelected",
        "areNodeContentsFullySelected",
        // todo: ideally, this should not be shared
        "resetActiveSelection",
        "focusEditable",
        // "collapseIfZWS",
        "isSelectionInEditable",
        "selectAroundNonEditable",
    ];
    resources = {
        user_commands: { id: "selectAll", run: this.selectAll.bind(this) },
        shortcuts: [{ hotkey: "control+a", commandId: "selectAll" }],
    };

    setup() {
        this.resetSelection();
        this.addDomListener(this.document, "selectionchange", () => {
            this.updateActiveSelection();
            const selection = this.document.getSelection();
            if (this.isSelectionInEditable(selection)) {
                scrollToSelection(selection);
            }
        });
        this.addDomListener(this.editable, "mousedown", (ev) => {
            if (ev.detail === 2) {
                this.correctDoubleClick = true;
            }
        });
        this.addDomListener(this.editable, "keydown", (ev) => {
            const handled = [
                "arrowright",
                "shift+arrowright",
                "arrowleft",
                "shift+arrowleft",
                "shift+arrowup",
                "shift+arrowdown",
            ];
            if (handled.includes(getActiveHotkey(ev))) {
                this.onKeyDownArrows(ev);
            }
        });
        this.addDomListener(this.editable, "click", (ev) => {
            if (ev.detail % 3 === 0) {
                this.onTripleClick(ev);
            }
        });
    }

    selectAll() {
        const selection = this.getEditableSelection();
        const containerSelector = "#wrap > *, .oe_structure > *, [contenteditable]";
        const container = selection && closestElement(selection.anchorNode, containerSelector);
        const [anchorNode, anchorOffset] = getDeepestPosition(container, 0);
        const [focusNode, focusOffset] = getDeepestPosition(container, nodeSize(container));
        this.setSelection({ anchorNode, anchorOffset, focusNode, focusOffset });
    }

    resetSelection() {
        this.activeSelection = this.makeActiveSelection();
    }

    onTripleClick() {
        const selectionData = this.getSelectionData();
        if (selectionData.documentSelectionIsInEditable) {
            const { documentSelection } = selectionData;
            const block = closestBlock(documentSelection.anchorNode);
            const [anchorNode, anchorOffset] = getDeepestPosition(block, 0);
            const [focusNode, focusOffset] = getDeepestPosition(block, nodeSize(block));
            this.setSelection({ anchorNode, anchorOffset, focusNode, focusOffset });
            return;
        }
    }

    /**
     * Update the active selection to the current selection in the editor.
     */
    updateActiveSelection() {
        this.previousActiveSelection = this.activeSelection;
        const selectionData = this.getSelectionData();
        if (selectionData.documentSelectionIsInEditable) {
            if (this.correctDoubleClick) {
                this.correctDoubleClick = false;
                const { anchorNode, anchorOffset, focusNode } = this.activeSelection;
                const anchorElement = closestElement(anchorNode);
                // Allow editing the text of a link after "double click" on the last word of said link.
                // This is done by correcting the selection focus inside of the link
                if (
                    anchorElement.tagName === "A" &&
                    anchorNode !== focusNode &&
                    focusNode.previousSibling === anchorElement
                ) {
                    const anchorElementLength = anchorElement.childNodes.length;

                    // Due to the ZWS added around links we can always expect
                    // the last childNode to be a ZWS in its own textNode.
                    // therefore we can safely set the selection focus before last node.
                    const newSelection = {
                        anchorNode: anchorNode,
                        anchorOffset: anchorOffset,
                        focusNode: anchorElement,
                        focusOffset: anchorElementLength - 1,
                    };
                    return this.setSelection(newSelection);
                }
            }

            if (this.fixSelectionOnEditableRoot(this.activeSelection)) {
                return;
            }
        }
        this.dispatchTo("selectionchange_handlers", selectionData);
    }

    /**
     * @param { Selection } [selection] The DOM selection
     * @return { EditorSelection }
     */
    makeActiveSelection(selection) {
        let range;
        let activeSelection;
        if (!selection || !selection.rangeCount) {
            activeSelection = {
                anchorNode: this.editable,
                anchorOffset: 0,
                focusNode: this.editable,
                focusOffset: 0,
                startContainer: this.editable,
                startOffset: 0,
                endContainer: this.editable,
                endOffset: 0,
                commonAncestorContainer: this.editable,
                isCollapsed: true,
                direction: DIRECTIONS.RIGHT,
                textContent: () => "",
                intersectsNode: () => false,
            };
        } else {
            range = selection.getRangeAt(0);
            let { anchorNode, anchorOffset, focusNode, focusOffset } = selection;
            let direction =
                anchorNode === range.startContainer ? DIRECTIONS.RIGHT : DIRECTIONS.LEFT;
            if (anchorNode === focusNode && focusOffset < anchorOffset) {
                direction = !direction;
            }
            if (
                this.activeSelection &&
                (isProtecting(anchorNode) ||
                    (isProtected(anchorNode) && !isUnprotecting(anchorNode)))
            ) {
                // Keep the previous activeSelection in case of user interactions
                // inside a protected zone.
                return this.activeSelection;
            }
            [anchorNode, anchorOffset] = normalizeSelfClosingElement(anchorNode, anchorOffset);
            [focusNode, focusOffset] = normalizeSelfClosingElement(focusNode, focusOffset);
            const [startContainer, startOffset, endContainer, endOffset] =
                direction === DIRECTIONS.RIGHT
                    ? [anchorNode, anchorOffset, focusNode, focusOffset]
                    : [focusNode, focusOffset, anchorNode, anchorOffset];
            range = this.document.createRange();
            range.setStart(startContainer, startOffset);
            range.setEnd(endContainer, endOffset);

            activeSelection = {
                anchorNode,
                anchorOffset,
                focusNode,
                focusOffset,
                startContainer,
                startOffset,
                endContainer,
                endOffset,
                commonAncestorContainer: range.commonAncestorContainer,
                isCollapsed: range.collapsed,
                direction,
                textContent: () => (range.collapsed ? "" : selection.toString()),
                intersectsNode: (node) => range.intersectsNode(node),
            };
        }

        Object.freeze(activeSelection);
        return activeSelection;
    }

    /**
     * @param { EditorSelection } selection
     */
    extractContent(selection) {
        const range = new Range();
        range.setStart(selection.startContainer, selection.startOffset);
        range.setEnd(selection.endContainer, selection.endOffset);
        this.setSelection({
            anchorNode: selection.startContainer,
            anchorOffset: selection.startOffset,
        });
        return range.extractContents();
    }

    /**
     * @param { Node } anchorNode
     * @param { number } anchorOffset
     * @param { Node } focusNode
     * @param { number } focusOffset
     * @param { boolean } direction
     *
     * @return { EditorSelection }
     */
    createEditorSelection(anchorNode, anchorOffset, focusNode, focusOffset, direction) {
        let startContainer, startOffset, endContainer, endOffset;
        const range = new Range();
        if (direction) {
            [startContainer, startOffset] = [anchorNode, anchorOffset];
            [endContainer, endOffset] = [focusNode, focusOffset];
        } else {
            [startContainer, startOffset] = [focusNode, focusOffset];
            [endContainer, endOffset] = [anchorNode, anchorOffset];
        }

        range.setStart(startContainer, startOffset);
        range.setEnd(endContainer, endOffset);
        return Object.freeze({
            ...this.activeSelection,
            anchorNode,
            anchorOffset,
            focusNode,
            focusOffset,
            startContainer,
            startOffset,
            endContainer,
            endOffset,
            commonAncestorContainer: range.commonAncestorContainer,
            cloneContents: () => range.cloneContents(),
        });
    }
    /**
     @return { EditorSelection }
     */
    getEditableSelection() {
        return this.getSelectionData().editableSelection;
    }

    /**
     * @return { SelectionData }
     */
    getSelectionData() {
        const selection = this.document.getSelection();
        const documentSelectionIsInEditable = selection && this.isSelectionInEditable(selection);
        const documentSelection =
            selection?.anchorNode && selection?.focusNode
                ? Object.freeze({
                      anchorNode: selection.anchorNode,
                      anchorOffset: selection.anchorOffset,
                      focusNode: selection.focusNode,
                      focusOffset: selection.focusOffset,
                      commonAncestorContainer: selection.rangeCount
                          ? selection.getRangeAt(0).commonAncestorContainer
                          : null,
                  })
                : null;
        if (documentSelectionIsInEditable) {
            this.activeSelection = this.makeActiveSelection(selection);
        } else if (!this.activeSelection.anchorNode.isConnected) {
            this.activeSelection = this.makeActiveSelection();
        }
        let { anchorNode, anchorOffset, focusNode, focusOffset, isCollapsed, direction } =
            this.activeSelection;

        const editableSelection = this.createEditorSelection(
            anchorNode,
            anchorOffset,
            focusNode,
            focusOffset,
            direction
        );

        const selectionData = {
            documentSelection: documentSelection,
            editableSelection: editableSelection,
            documentSelectionIsInEditable: documentSelectionIsInEditable,
        };

        Object.defineProperty(selectionData, "deepEditableSelection", {
            get: function () {
                // Transform the selection to return the depest possible node.
                [anchorNode, anchorOffset] = getDeepestPosition(anchorNode, anchorOffset);
                [focusNode, focusOffset] = isCollapsed
                    ? [anchorNode, anchorOffset]
                    : getDeepestPosition(focusNode, focusOffset);
                return this.createEditorSelection(
                    anchorNode,
                    anchorOffset,
                    focusNode,
                    focusOffset,
                    direction
                );
            }.bind(this),
        });

        Object.defineProperty(selectionData, "documentSelectionIsProtecting", {
            get: function () {
                return documentSelection?.anchorNode
                    ? isProtecting(documentSelection.anchorNode)
                    : false;
            }.bind(this),
        });
        Object.defineProperty(selectionData, "documentSelectionIsProtected", {
            get: function () {
                return documentSelection?.anchorNode
                    ? isProtected(documentSelection.anchorNode)
                    : false;
            }.bind(this),
        });

        return Object.freeze(selectionData);
    }

    /**
     * Returns true if selection is valid and in the editable.
     * Otherwise, returns false and logs a warning.
     */
    validateSelection({ anchorNode, anchorOffset, focusNode, focusOffset }) {
        const validateNode = (node) => {
            if (!this.editable.contains(node)) {
                console.warn("Invalid selection. Node is not part of the editable:", node);
                return false;
            }
            return true;
        };
        const validateOffset = (node, offset) => {
            if (offset < 0 || offset > nodeSize(node)) {
                console.warn("Invalid selection. Offset is out of bounds:", offset, node);
                return false;
            }
            return true;
        };
        const isCollapsed = anchorNode === focusNode && anchorOffset === focusOffset;
        return (
            validateNode(anchorNode) &&
            (focusNode === anchorNode || validateNode(focusNode)) &&
            validateOffset(anchorNode, anchorOffset) &&
            (isCollapsed || validateOffset(focusNode, focusOffset))
        );
    }

    /**
     * Set the selection in the editor.
     *
     * @param { Object } selection
     * @param { Node } selection.anchorNode
     * @param { number } selection.anchorOffset
     * @param { Node } [selection.focusNode=selection.anchorNode]
     * @param { number } [selection.focusOffset=selection.anchorOffset]
     * @param { Object } [options]
     * @param { boolean } [options.normalize=true] Normalize deep the selection
     * @return { EditorSelection | null }
     */
    setSelection(
        { anchorNode, anchorOffset, focusNode = anchorNode, focusOffset = anchorOffset },
        { normalize = true } = {}
    ) {
        if (!this.validateSelection({ anchorNode, anchorOffset, focusNode, focusOffset })) {
            return null;
        }
        const isCollapsed = anchorNode === focusNode && anchorOffset === focusOffset;
        [focusNode, focusOffset] = normalizeSelfClosingElement(focusNode, focusOffset, "right");
        [anchorNode, anchorOffset] = isCollapsed
            ? [focusNode, focusOffset]
            : normalizeSelfClosingElement(anchorNode, anchorOffset, "left");
        if (normalize) {
            // normalize selection
            [anchorNode, anchorOffset] = normalizeDeepCursorPosition(anchorNode, anchorOffset);
            [focusNode, focusOffset] = isCollapsed
                ? [anchorNode, anchorOffset]
                : normalizeDeepCursorPosition(focusNode, focusOffset);
        }

        [anchorNode, anchorOffset] = normalizeFakeBR(anchorNode, anchorOffset);
        [focusNode, focusOffset] = normalizeFakeBR(focusNode, focusOffset);
        const selection = this.document.getSelection();
        const documentSelectionIsInEditable = selection && this.isSelectionInEditable(selection);
        if (selection) {
            if (documentSelectionIsInEditable || selection.anchorNode === null) {
                selection.setBaseAndExtent(anchorNode, anchorOffset, focusNode, focusOffset);
                this.activeSelection = this.makeActiveSelection(selection, true);
            } else {
                let range = new Range();
                range.setStart(anchorNode, anchorOffset);
                range.setEnd(focusNode, focusOffset);
                if (anchorNode !== focusNode || anchorOffset !== focusOffset) {
                    // Check if the direction is correct
                    if (range.collapsed) {
                        range = new Range();
                        range.setEnd(anchorNode, anchorOffset);
                        range.setStart(focusNode, focusOffset);
                    }
                }

                this.activeSelection = this.makeActiveSelection({
                    anchorNode,
                    anchorOffset,
                    focusNode,
                    focusOffset,
                    getRangeAt: () => range,
                    rangeCount: 1,
                });
            }
        }

        return this.activeSelection;
    }

    /**
     * Set the cursor at the start of the given node.
     * @param { Node } node
     */
    setCursorStart(node) {
        return this.setSelection({ anchorNode: node, anchorOffset: 0 });
    }

    /**
     * Set the cursor at the end of the given node.
     * @param { Node } node
     */
    setCursorEnd(node) {
        return this.setSelection({ anchorNode: node, anchorOffset: nodeSize(node) });
    }

    /**
     * Stores the current selection and returns an object with methods to:
     * - update the cursors (anchor and focus) node and offset after DOM
     * manipulations that migh affect them. Such methods are chainable.
     * - restore the updated selection.
     * @returns {Cursors}
     */
    preserveSelection() {
        const hadSelection =
            this.document.getSelection() && this.document.getSelection().anchorNode !== null;
        const selectionData = this.getSelectionData();
        const selection = selectionData.editableSelection;
        const anchor = { node: selection.anchorNode, offset: selection.anchorOffset };
        const focus = { node: selection.focusNode, offset: selection.focusOffset };

        return {
            restore: () => {
                if (!hadSelection) {
                    return;
                }
                this.setSelection(
                    {
                        anchorNode: anchor.node,
                        anchorOffset: anchor.offset,
                        focusNode: focus.node,
                        focusOffset: focus.offset,
                    },
                    { normalize: false }
                );
            },
            update(callback) {
                callback(anchor);
                callback(focus);
                return this;
            },
            remapNode(node, newNode) {
                return this.update((cursor) => {
                    if (cursor.node === node) {
                        cursor.node = newNode;
                    }
                });
            },
            setOffset(node, newOffset) {
                return this.update((cursor) => {
                    if (cursor.node === node) {
                        cursor.offset = newOffset;
                    }
                });
            },
            shiftOffset(node, shiftOffset) {
                return this.update((cursor) => {
                    if (cursor.node === node) {
                        cursor.offset += shiftOffset;
                    }
                });
            },
        };
    }

    /**
     * Returns a function that returns true if the given node's contents are
     * fully selected.
     *
     * @param {Node} node
     * @param {boolean} [_useLeaves=true] @deprecated this is a legacy argument,
     *                                    only used to preserve the behavior of
     *                                    deprecated methods.
     * @returns {() => boolean}
     */
    areNodeContentsFullySelected(node, _useLeaves = true) {
        const selection = this.getEditableSelection();
        const range = new Range();
        range.setStart(selection.startContainer, selection.startOffset);
        range.setEnd(selection.endContainer, selection.endOffset);

        const firstLeafNode = _useLeaves ? firstLeaf(node) : node;
        const lastLeafNode = _useLeaves ? lastLeaf(node) : node;
        return (
            // Custom rules
            this.getResource("fully_selected_node_predicates").some((cb) => cb(node, selection)) ||
            // Default rule
            (range.isPointInRange(firstLeafNode, 0) &&
                range.isPointInRange(lastLeafNode, nodeSize(lastLeafNode)))
        );
    }

    /**
     * @deprecated use `getTargetedNodes` instead.
     *
     * Returns an array containing all the nodes fully contained in the selection.
     *
     * @returns {Node[]}
     */
    getSelectedNodes() {
        return this.getTraversedNodes().filter((node) =>
            this.areNodeContentsFullySelected(node, false)
        );
    }

    isNodeContentsFullySelected(node) {
        const selection = this.getEditableSelection();
        const range = new Range();
        range.setStart(selection.startContainer, selection.startOffset);
        range.setEnd(selection.endContainer, selection.endOffset);

        const firstLeafNode = firstLeaf(node);
        const lastLeafNode = lastLeaf(node);
        return (
            range.isPointInRange(firstLeafNode, 0) &&
            range.isPointInRange(lastLeafNode, nodeSize(lastLeafNode))
        );
    }

    /**
     * @deprecated use `getTargetedNodes` instead.
     *
     * Returns the nodes intersected by the current selection, up to the common
     * ancestor container (inclusive).
     *
     * @returns {Node[]}
     */
    getTraversedNodes() {
        const selection = this.getSelectionData().deepEditableSelection;
        const { commonAncestorContainer: root } = selection;

        let traversedNodes = [
            root,
            ...descendants(root).filter((node) => selection.intersectsNode(node)),
        ];

        const modifiers = [
            // Remove the editable from the list
            (nodes) => (nodes[0] === this.editable ? nodes.slice(1) : nodes),
            // Filter out nodes that have no content selected
            (nodes) => {
                const edgeNodes = getUnselectedEdgeNodes(selection);
                return nodes.filter((node) => !edgeNodes.has(node));
            },
            // Custom modifiers
            ...this.getResource("traversed_nodes_processors"),
        ];

        for (const modifier of modifiers) {
            traversedNodes = modifier(traversedNodes);
        }

        return traversedNodes;
    }

    /**
     * Returns the nodes targeted by the current selection, from top to bottom
     * and left to right.
     * This includes nodes intersected by the selection, as well as the deepest
     * anchor and offset nodes that are at least partly contained in the
     * selection.
     * An element is considered intersected by the selection when reading the
     * normalized selection's HTML contents would involve reading the opening or
     * closing tags of the element.
     * A collapsed selection returns the node in which it is collapsed.
     *
     * @example
     * <p>a[]b</p> -> ["ab"]
     * @example
     * <p>a[b</p><h1>c]d</h1> -> [P, "ab", H1, "cd"]
     * @example
     * <p>a[b</p><h1>]cd</h1> -> [P, "ab", H1]
     * @example
     * <div><p>a[b</p><h1>cd</h1></div><h2>e]f</h2> -> [DIV, P, "ab", H1, "cd", H2, "ef"]
     *
     * @returns {Node[]}
     */
    getTargetedNodes() {
        const selectionData = this.getSelectionData();
        const selection = selectionData.deepEditableSelection;
        const { commonAncestorContainer: root } = selectionData.editableSelection;

        let targetedNodes = [];
        if (selection.isCollapsed && selection.anchorNode.nodeType !== Node.TEXT_NODE) {
            targetedNodes = [root];
        }
        targetedNodes.push(...descendants(root));
        if (!targetedNodes.length) {
            targetedNodes = [root];
        }

        targetedNodes = targetedNodes.filter(
            (node) =>
                selectionData.editableSelection.intersectsNode(node) ||
                (node.nodeType === Node.TEXT_NODE &&
                    (node === selection.anchorNode || node === selection.focusNode))
        );

        const modifiers = [
            // Remove the editable from the list
            (nodes) => (nodes[0] === this.editable ? nodes.slice(1) : nodes),
            // Filter out text nodes that have no content selected
            (nodes) => {
                if (selection.isCollapsed) {
                    return nodes;
                } else {
                    const edgeTextNodes = new Set(
                        [...getUnselectedEdgeNodes(selection)].filter(
                            (node) => node.nodeType === Node.TEXT_NODE
                        )
                    );
                    return nodes.filter((node) => !edgeTextNodes.has(node));
                }
            },
            // Custom modifiers
            ...this.getResource("traversed_nodes_processors"),
        ];
        for (const modifier of modifiers) {
            targetedNodes = modifier(targetedNodes);
        }
        return targetedNodes;
    }

    /**
     * @deprecated use `getTargetedBlocks` instead.
     *
     * Returns a Set of traversed blocks within the given range.
     *
     * @returns {Set<HTMLElement>}
     */
    getTraversedBlocks() {
        return new Set(this.getTraversedNodes().map(closestBlock).filter(Boolean));
    }

    /**
     * Returns a Set of targeted blocks within the given range.
     *
     * @returns {Set<HTMLElement>}
     */
    getTargetedBlocks() {
        return new Set(this.getTargetedNodes().map(closestBlock).filter(Boolean));
    }
    resetActiveSelection() {
        const selection = this.document.getSelection();
        selection.setBaseAndExtent(
            this.previousActiveSelection.anchorNode,
            this.previousActiveSelection.anchorOffset,
            this.previousActiveSelection.focusNode,
            this.previousActiveSelection.focusOffset
        );
    }

    // @todo @phoenix we should find a real use case and test it
    // /**
    //  * Set a deep selection that split the text and collapse it if only one ZWS is
    //  * selected.
    //  *
    //  * @returns {boolean} true if the selection has only one ZWS.
    //  */
    // collapseIfZWS() {
    //     const selection = this.getSelectionData().deepEditableSelection;
    //     if (
    //         selection.startContainer === selection.endContainer &&
    //         selection.startContainer.nodeType === Node.TEXT_NODE &&
    //         selection.startContainer.textContent === "\u200B"
    //     ) {
    //         // We Collapse the selection and bypass deleteRange
    //         // if the range content is only one ZWS.
    //         this.setCursorStart(selection.startContainer);
    //         return true;
    //     }
    //     return false;
    // }

    /**
     * Places the cursor in a safe place (not the editable root).
     * Inserts an empty paragraph if selection results from mouse click and
     * there's no other way to insert text before/after a block.
     *
     * @param {Selection} selection - Collapsed selection at the editable root.
     */
    fixSelectionOnEditableRoot(selection) {
        if (!selection.isCollapsed || selection.anchorNode !== this.editable) {
            return false;
        }

        this.dispatchTo("fix_selection_on_editable_root_handlers", selection);
    }

    /**
     * This function adjusts a given selection to the current nodeSize of its
     * anchorNode and focusNode, only if they are both present in the given
     * editable. Apply and return: a valid given selection, a modified
     * selection if some offset needed to be adjusted. Do nothing if the given
     * selection anchor or focus nodes are not in this.editable.
     *
     * @param { Object } selection
     * @param { Node } selection.anchorNode
     * @param { number } selection.anchorOffset
     * @param { Node } selection.focusNode
     * @param { number } selection.focusOffset
     * @returns { EditorSelection|null } selection, rectified selection or null
     */
    rectifySelection(selection) {
        if (!this.isSelectionInEditable(selection)) {
            return null;
        }
        const anchorNode = selection.anchorNode;
        let anchorOffset = selection.anchorOffset;
        const focusNode = selection.focusNode;
        let focusOffset = selection.focusOffset;
        const anchorSize = nodeSize(anchorNode);
        const focusSize = nodeSize(focusNode);
        if (anchorSize < anchorOffset) {
            anchorOffset = anchorSize;
        }
        if (focusSize < focusOffset) {
            focusOffset = focusSize;
        }
        const anchorTarget = childNodes(anchorNode).at(anchorOffset);
        const focusTarget = childNodes(focusNode).at(focusOffset);
        const protectionCheck = (node) =>
            isProtecting(node) || (isProtected(node) && !isUnprotecting(node));
        if (
            focusTarget !== anchorTarget &&
            focusTarget.previousSibling === anchorTarget &&
            protectionCheck(anchorTarget)
        ) {
            return;
        }
        if (protectionCheck(anchorNode) || protectionCheck(focusNode)) {
            // TODO @phoenix, TODO ABD: better handle setSelection on protected
            // elements
            return;
        }
        return this.setSelection({
            anchorNode,
            anchorOffset,
            focusNode,
            focusOffset,
        });
    }

    /**
     * @param {"move"|"extend"} alter
     * @param {"backward"|"forward"} direction
     * @param {"character"|"word"|"line"} granularity
     * @returns {EditorSelection}
     */
    modifySelection(alter, direction, granularity) {
        const selectionData = this.getSelectionData();
        if (!selectionData.documentSelectionIsInEditable) {
            return selectionData.editableSelection;
        }
        const selection = this.document.getSelection();
        if (!selection) {
            return selectionData.editableSelection;
        }
        selection.modify(alter, direction, granularity);
        if (!this.isSelectionInEditable(selection)) {
            // If selection was moved to outside the editable, restore it.
            return this.setSelection(selectionData.editableSelection);
        }
        this.activeSelection = this.makeActiveSelection(selection);
        return this.activeSelection;
    }

    /**
     * Changes the selection before the browser's default behavior moves the
     * cursor, in order to skip undesired characters (typically invisible
     * characters).
     */
    onKeyDownArrows(ev) {
        const selection = this.document.getSelection();
        if (!selection || !this.isSelectionInEditable(selection)) {
            return;
        }

        // Whether moving a collapsed cursor or extending a selection.
        const mode = ev.shiftKey ? "extend" : "move";

        if (["ArrowLeft", "ArrowRight"].includes(ev.key)) {
            // Direction of the movement (take rtl writing into account)
            const screenDirection = ev.key === "ArrowLeft" ? "left" : "right";
            const isRtl = closestElement(selection.focusNode, "[dir]")?.dir === "rtl";
            const domDirection = (screenDirection === "left") ^ isRtl ? "previous" : "next";

            // Whether the character next to the cursor should be skipped.
            const shouldSkipCallbacks = this.getResource(
                "intangible_char_for_keyboard_navigation_predicates"
            );
            let adjacentCharacter = getAdjacentCharacter(selection, domDirection, this.editable);
            let shouldSkip = shouldSkipCallbacks.some((cb) => cb(ev, adjacentCharacter));

            while (shouldSkip) {
                const { focusNode: nodeBefore, focusOffset: offsetBefore } = selection;

                selection.modify(mode, screenDirection, "character");

                const hasSelectionChanged =
                    nodeBefore !== selection.focusNode || offsetBefore !== selection.focusOffset;
                const lastSkippedChar = adjacentCharacter;
                adjacentCharacter = getAdjacentCharacter(selection, domDirection, this.editable);

                shouldSkip =
                    hasSelectionChanged &&
                    shouldSkipCallbacks.some((cb) => cb(ev, adjacentCharacter, lastSkippedChar));
            }
        }

        const { focusNode, focusOffset } = selection;
        if (mode === "extend") {
            // Since selection can't traverse contenteditable="false" elements,
            // we adjust the selection to the sibling of non editable element.
            const selectingBackward = ["ArrowLeft", "ArrowUp"].includes(ev.key);
            const currentBlock = closestBlock(focusNode);
            const isAtBoundary = selectingBackward
                ? firstLeaf(currentBlock) === focusNode && focusOffset === 0
                : lastLeaf(currentBlock) === focusNode && focusOffset === nodeSize(focusNode);
            const adjacentBlock = selectingBackward
                ? currentBlock.previousElementSibling
                : currentBlock.nextElementSibling;
            const targetBlock = selectingBackward
                ? adjacentBlock?.previousElementSibling
                : adjacentBlock?.nextElementSibling;
            if (!adjacentBlock?.isContentEditable && targetBlock && isAtBoundary) {
                const leafNode = selectingBackward ? lastLeaf(targetBlock) : firstLeaf(targetBlock);
                const offset = selectingBackward ? nodeSize(leafNode) : 0;
                selection.extend(leafNode, offset);
                ev.preventDefault();
            }
        }
    }

    isSelectionInEditable({ anchorNode, focusNode } = {}) {
        return (
            !!anchorNode &&
            !!focusNode &&
            this.editable.contains(anchorNode) &&
            (focusNode === anchorNode || this.editable.contains(focusNode))
        );
    }

    focusEditable() {
        const { editableSelection, documentSelectionIsInEditable } = this.getSelectionData();
        if (documentSelectionIsInEditable) {
            return;
        }
        // Manualy focusing the editable is necessary to avoid some non-deterministic error in the HOOT unit tests.
        this.editable.focus({ preventScroll: true });
        const { anchorNode, anchorOffset, focusNode, focusOffset } = editableSelection;
        const selection = this.document.getSelection();
        if (selection) {
            selection.setBaseAndExtent(anchorNode, anchorOffset, focusNode, focusOffset);
        }
    }

    /**
     * @returns {EditorSelection}
     */
    selectAroundNonEditable() {
        // Get up-to-date selection
        const { editableSelection } = this.getSelectionData();
        // Avoid setting the selection if it's not inside an uneditable element
        const isInUneditable = (node) => !!closestElement(node, (elem) => !elem.isContentEditable);
        let { startContainer: start, endContainer: end } = editableSelection;
        if (!(isInUneditable(start) || (end !== start && isInUneditable(end)))) {
            return editableSelection;
        }
        // Normalize both sides
        let { startOffset, endOffset, direction } = editableSelection;
        [start, startOffset] = normalizeNotEditableNode(start, startOffset, "left");
        [end, endOffset] = normalizeNotEditableNode(end, endOffset, "right");
        // Set the new selection
        const [anchorNode, anchorOffset, focusNode, focusOffset] = direction
            ? [start, startOffset, end, endOffset]
            : [end, endOffset, start, startOffset];
        return this.setSelection({ anchorNode, anchorOffset, focusNode, focusOffset });
    }
}
