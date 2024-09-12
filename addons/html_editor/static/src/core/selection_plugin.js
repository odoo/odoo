import { closestBlock } from "@html_editor/utils/blocks";
import {
    getDeepestPosition,
    isMediaElement,
    isProtected,
    isProtecting,
    isTextNode,
    paragraphRelatedElements,
    previousLeaf,
} from "@html_editor/utils/dom_info";
import { closestElement, descendants } from "@html_editor/utils/dom_traversal";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Plugin } from "../plugin";
import { DIRECTIONS, boundariesIn, endPos, leftPos, nodeSize, rightPos } from "../utils/position";
import {
    getAdjacentCharacter,
    normalizeCursorPosition,
    normalizeDeepCursorPosition,
    normalizeFakeBR,
} from "../utils/selection";

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

/**
 * @returns edges nodes if they do not have content selected
 */
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

export class SelectionPlugin extends Plugin {
    static name = "selection";
    static shared = [
        "getSelectionData",
        "getEditableSelection",
        "setSelection",
        "setCursorStart",
        "setCursorEnd",
        "extractContent",
        "preserveSelection",
        "resetSelection",
        "getSelectedNodes",
        "getTraversedNodes",
        "getTraversedBlocks",
        "modifySelection",
        "rectifySelection",
        // "collapseIfZWS",
    ];
    static resources = (p) => ({
        shortcuts: [{ hotkey: "control+a", command: "SELECT_ALL" }],
    });

    setup() {
        this.canApplySelectionToDocument = true;
        this.resetSelection();
        this.addDomListener(this.document, "selectionchange", this.updateActiveSelection);
        this.addDomListener(this.editable, "mousedown", (ev) => {
            if (ev.detail >= 3) {
                this.correctTripleClick = true;
            }
        });
        this.addDomListener(this.editable, "keydown", (ev) => {
            this.currentKeyDown = ev.key;
            const handled = ["arrowright", "shift+arrowright", "arrowleft", "shift+arrowleft"];
            if (handled.includes(getActiveHotkey(ev))) {
                this.onKeyDownArrows(ev);
            }
        });
        this.addDomListener(this.editable, "pointerdown", () => {
            this.isPointerDown = true;
        });
        this.addDomListener(this.editable, "pointerup", () => {
            this.isPointerDown = false;
            this.preventNextPointerdownFix = false;
        });
    }

    handleCommand(command, payload) {
        switch (command) {
            case "SELECT_ALL":
                {
                    const selection = this.getEditableSelection();
                    const containerSelector = "#wrap > *, .oe_structure > *, [contenteditable]";
                    const container =
                        selection && closestElement(selection.anchorNode, containerSelector);
                    const [anchorNode, anchorOffset, focusNode, focusOffset] =
                        boundariesIn(container);
                    this.setSelection({ anchorNode, anchorOffset, focusNode, focusOffset });
                }
                break;
        }
    }

    resetSelection() {
        this.activeSelection = this.makeActiveSelection();
    }

    /**
     * Update the active selection to the current selection in the editor.
     */
    updateActiveSelection() {
        this.previousActiveSelection = this.activeSelection;
        const selectionData = this.getSelectionData();
        if (selectionData.documentSelectionIsInEditable) {
            if (this.correctTripleClick) {
                this.correctTripleClick = false;
                let { anchorNode, anchorOffset, focusNode, focusOffset } = this.activeSelection;
                if (focusOffset === 0 && anchorNode !== focusNode) {
                    [focusNode, focusOffset] = endPos(previousLeaf(focusNode));
                    return this.setSelection({ anchorNode, anchorOffset, focusNode, focusOffset });
                }
            }

            if (this.fixSelectionOnEditableRoot(this.activeSelection)) {
                return;
            }
        }
        for (const handler of this.resources.onSelectionChange || []) {
            handler(selectionData);
        }
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
                isDefault: true,
            };
        } else {
            range = selection.getRangeAt(0);
            let { anchorNode, anchorOffset, focusNode, focusOffset } = selection;
            let direction =
                anchorNode === range.startContainer ? DIRECTIONS.RIGHT : DIRECTIONS.LEFT;
            if (anchorNode === focusNode && focusOffset < anchorOffset) {
                direction = !direction;
            }

            [anchorNode, anchorOffset] = normalizeCursorPosition(
                anchorNode,
                anchorOffset,
                direction ? "left" : "right"
            );
            [focusNode, focusOffset] = normalizeCursorPosition(
                focusNode,
                focusOffset,
                direction ? "right" : "left"
            );
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
                isDefault: false,
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
        const documentSelection = selection
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
                    ? isProtected(documentSelection.anchorNode)
                    : false;
            }.bind(this),
        });
        Object.defineProperty(selectionData, "documentSelectionIsProtected", {
            get: function () {
                return documentSelection?.anchorNode
                    ? isProtecting(documentSelection.anchorNode)
                    : false;
            }.bind(this),
        });

        return Object.freeze(selectionData);
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
     * @return { EditorSelection }
     */
    setSelection(
        { anchorNode, anchorOffset, focusNode = anchorNode, focusOffset = anchorOffset },
        { normalize = true } = {}
    ) {
        if (!this.isSelectionInEditable({ anchorNode, focusNode })) {
            throw new Error("Selection is not in editor");
        }
        [anchorNode, anchorOffset] = normalizeCursorPosition(anchorNode, anchorOffset, "left");
        [focusNode, focusOffset] = normalizeCursorPosition(focusNode, focusOffset, "right");
        if (normalize) {
            const isCollapsed = anchorNode === focusNode && anchorOffset === focusOffset;
            // normalize selection
            [anchorNode, anchorOffset] = normalizeDeepCursorPosition(anchorNode, anchorOffset);
            [focusNode, focusOffset] = isCollapsed
                ? [anchorNode, anchorOffset]
                : normalizeDeepCursorPosition(focusNode, focusOffset);
        }

        [anchorNode, anchorOffset] = normalizeFakeBR(anchorNode, anchorOffset);
        [focusNode, focusOffset] = normalizeFakeBR(focusNode, focusOffset);
        const selection = this.document.getSelection();
        if (selection) {
            if (this.canApplySelectionToDocument) {
                if (
                    selection.anchorNode !== anchorNode ||
                    selection.focusNode !== focusNode ||
                    selection.anchorOffset !== anchorOffset ||
                    selection.focusOffset !== focusOffset
                ) {
                    selection.setBaseAndExtent(anchorNode, anchorOffset, focusNode, focusOffset);
                }
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
        const selectionData = this.getSelectionData();
        const selection = selectionData.editableSelection;
        const anchor = { node: selection.anchorNode, offset: selection.anchorOffset };
        const focus = { node: selection.focusNode, offset: selection.focusOffset };

        this.canApplySelectionToDocument = selectionData.documentSelectionIsInEditable;
        return {
            restore: () => {
                if (selection.isDefault) {
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
                this.canApplySelectionToDocument = true;
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
     * Returns an array containing all the nodes fully contained in the selection.
     *
     * @returns {Node[]}
     */
    getSelectedNodes() {
        const selection = this.getSelectionData().editableSelection;
        const range = new Range();
        range.setStart(selection.startContainer, selection.startOffset);
        range.setEnd(selection.endContainer, selection.endOffset);
        const isNodeFullySelected = (node) =>
            // Custom rules
            this.resources.considerNodeFullySelected?.some((cb) => cb(node, selection)) ||
            // Default rule
            (range.isPointInRange(node, 0) && range.isPointInRange(node, nodeSize(node)));
        return this.getTraversedNodes().filter(isNodeFullySelected);
    }

    /**
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
            // Filter whitespace
            (nodes) => {
                return nodes.filter((node) => !isTextNode(node) || node.textContent !== "\n");
            },
            // Custom modifiers
            ...(this.resources.modifyTraversedNodes || []),
        ];

        for (const modifier of modifiers) {
            traversedNodes = modifier(traversedNodes);
        }

        return traversedNodes;
    }

    /**
     * Returns a Set of traversed blocks within the given range.
     *
     * @returns {Set<HTMLElement>}
     */
    getTraversedBlocks() {
        return new Set(this.getTraversedNodes().map(closestBlock).filter(Boolean));
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
        if (
            !(
                selection.isCollapsed &&
                selection.anchorNode === this.editable &&
                !this.config.allowInlineAtRoot
            )
        ) {
            return false;
        }

        const nodeAfterCursor = this.editable.childNodes[selection.anchorOffset];
        const nodeBeforeCursor = nodeAfterCursor && nodeAfterCursor.previousElementSibling;

        return (
            this.fixSelectionOnEditableRootArrowKeys(nodeAfterCursor, nodeBeforeCursor) ||
            this.fixSelectionOnEditableRootGeneric(nodeAfterCursor, nodeBeforeCursor) ||
            this.fixSelectionOnEditableRootCreateP(nodeAfterCursor, nodeBeforeCursor)
        );
    }
    /**
     * @param {Node} nodeAfterCursor
     * @param {Node} nodeBeforeCursor
     * @returns {boolean}
     */
    fixSelectionOnEditableRootArrowKeys(nodeAfterCursor, nodeBeforeCursor) {
        const currentKeyDown = this.currentKeyDown;
        delete this.currentKeyDown;
        if (currentKeyDown === "ArrowRight" || currentKeyDown === "ArrowDown") {
            while (nodeAfterCursor && isNotAllowedContent(nodeAfterCursor)) {
                nodeAfterCursor = nodeAfterCursor.nextElementSibling;
            }
            const [anchorNode] = getDeepestPosition(nodeAfterCursor, 0);
            if (nodeAfterCursor) {
                this.setSelection({ anchorNode: anchorNode, anchorOffset: 0 });
                return true;
            } else {
                this.resetActiveSelection();
            }
        } else if (currentKeyDown === "ArrowLeft" || currentKeyDown === "ArrowUp") {
            while (nodeBeforeCursor && isNotAllowedContent(nodeBeforeCursor)) {
                nodeBeforeCursor = nodeBeforeCursor.previousElementSibling;
            }
            if (nodeBeforeCursor) {
                const [anchorNode, anchorOffset] = getDeepestPosition(
                    nodeBeforeCursor,
                    nodeSize(nodeBeforeCursor)
                );
                this.setSelection({
                    anchorNode: anchorNode,
                    anchorOffset: anchorOffset,
                });
                return true;
            } else {
                this.resetActiveSelection();
            }
        }
    }
    /**
     * @param {Node} nodeAfterCursor
     * @param {Node} nodeBeforeCursor
     * @returns {boolean}
     */
    fixSelectionOnEditableRootGeneric(nodeAfterCursor, nodeBeforeCursor) {
        // Handle arrow key presses.
        if (nodeAfterCursor && paragraphRelatedElements.includes(nodeAfterCursor.nodeName)) {
            // Cursor is right before a 'P'.
            this.setCursorStart(nodeAfterCursor);
            return true;
        } else if (
            nodeBeforeCursor &&
            paragraphRelatedElements.includes(nodeBeforeCursor.nodeName)
        ) {
            // Cursor is right after a 'P'.
            this.setCursorEnd(nodeBeforeCursor);
            return true;
        }
    }
    /**
     * Handle cursor not next to a 'P'.
     * Insert a new 'P' if selection resulted from a mouse click.
     *
     * In some situations (notably around tables and horizontal
     * separators), the cursor could be placed having its anchorNode at
     * the editable root, allowing the user to insert inlined text at
     * it.
     *
     * @param {Node} nodeAfterCursor
     * @param {Node} nodeBeforeCursor
     * @returns {boolean}
     */
    fixSelectionOnEditableRootCreateP(nodeAfterCursor, nodeBeforeCursor) {
        if (this.isPointerDown && !this.preventNextPointerdownFix) {
            // The setSelection at the end of this fix could trigger another
            // setSelection (that would re-trigger this fix). So this flag is
            // used to prevent to fix twice from the same mouse event.
            this.preventNextPointerdownFix = true;

            const p = this.document.createElement("p");
            p.append(this.document.createElement("br"));
            if (!nodeAfterCursor) {
                // Cursor is at the end of the editable.
                this.editable.append(p);
            } else if (!nodeBeforeCursor) {
                // Cursor is at the beginning of the editable.
                this.editable.prepend(p);
            } else {
                // Cursor is between two non-p blocks
                nodeAfterCursor.before(p);
            }
            this.setCursorStart(p);
            this.dispatch("ADD_STEP");
            return true;
        }
        return false;
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
        const anchorSize = nodeSize(selection.anchorNode);
        const focusSize = nodeSize(selection.focusNode);
        if (anchorSize < selection.anchorOffset || focusSize < selection.focusOffset) {
            return this.setSelection({
                anchorNode: selection.anchorNode,
                anchorOffset: anchorSize,
                focusNode: selection.focusNode,
                focusOffset: focusSize,
            });
        } else {
            return this.setSelection(selection);
        }
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

        // Direction of the movement (take rtl writing into account)
        const screenDirection = ev.key === "ArrowLeft" ? "left" : "right";
        const isRtl = closestElement(selection.focusNode, "[dir]")?.dir === "rtl";
        const domDirection = (screenDirection === "left") ^ isRtl ? "previous" : "next";

        // Whether the character next to the cursor should be skipped.
        const shouldSkipCallbacks = this.resources.arrows_should_skip || [];
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

    isSelectionInEditable({ anchorNode, focusNode }) {
        return (
            this.editable.contains(anchorNode) &&
            (focusNode === anchorNode || this.editable.contains(focusNode))
        );
    }
}
