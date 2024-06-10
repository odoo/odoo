import { closestBlock } from "@html_editor/utils/blocks";
import {
    getDeepestPosition,
    previousLeaf,
    isProtected,
    paragraphRelatedElements,
    isMediaElement,
} from "@html_editor/utils/dom_info";
import { closestElement, descendants } from "@html_editor/utils/dom_traversal";
import { Plugin } from "../plugin";
import { DIRECTIONS, endPos, nodeSize } from "../utils/position";
import {
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
 * @property { boolean } inEditable
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

export class SelectionPlugin extends Plugin {
    static name = "selection";
    static shared = [
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
        "extendSelection",
        // "collapseIfZWS",
    ];

    setup() {
        this.resetSelection();
        this.addDomListener(this.document, "selectionchange", this.updateActiveSelection);
        this.addDomListener(this.editable, "mousedown", (ev) => {
            if (ev.detail >= 3) {
                this.correctTripleClick = true;
            }
        });
        this.addDomListener(this.editable, "keydown", (ev) => {
            this.currentKeyDown = ev.key;
        });
        this.addDomListener(this.editable, "pointerdown", () => {
            this.isPointerDown = true;
        });
        this.addDomListener(this.editable, "pointerup", () => {
            this.isPointerDown = false;
            this.preventNextMousedownFix = false;
        });
    }

    resetSelection() {
        this.activeSelection = this.makeSelection();
    }

    /**
     * Update the active selection to the current selection in the editor.
     */
    updateActiveSelection() {
        const selection = this.document.getSelection();
        let inEditable;
        if (!selection || selection.rangeCount === 0) {
            inEditable = false;
        } else {
            const range = selection.getRangeAt(0);
            inEditable =
                this.editable.contains(range.commonAncestorContainer) &&
                !isProtected(range.commonAncestorContainer);
        }
        let newSelection;
        if (inEditable) {
            if (this.correctTripleClick) {
                this.correctTripleClick = false;
                let { anchorNode, anchorOffset, focusNode, focusOffset } = selection;
                if (focusOffset === 0 && anchorNode !== focusNode) {
                    [focusNode, focusOffset] = endPos(previousLeaf(focusNode));
                    return this.setSelection({ anchorNode, anchorOffset, focusNode, focusOffset });
                }
            }
            newSelection = this.makeSelection(selection, inEditable);
        } else {
            newSelection = Object.freeze({ ...this.activeSelection, inEditable: false });
        }

        if (this.fixSelectionOnEditableRoot(newSelection)) {
            return;
        }
        this.activeSelection = newSelection;
        const activeSelection = this.activeSelection;
        for (const handler of this.resources.onSelectionChange || []) {
            handler(activeSelection);
        }
    }

    /**
     * @param { Selection } [selection] The DOM selection
     * @param { boolean } [inEditable]
     * @return { EditorSelection }
     */
    makeSelection(selection, inEditable = false) {
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
                textContent: "",
                inEditable,
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
                textContent: range.collapsed ? "" : selection.toString(),
                inEditable,
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
        return range.extractContents();
    }

    /**
     * @return { EditorSelection }
     */
    getEditableSelection({ deep = false } = {}) {
        const selection = this.document.getSelection();
        if (
            selection &&
            selection.rangeCount &&
            this.editable.contains(selection.anchorNode) &&
            (selection.focusNode === selection.anchorNode ||
                this.editable.contains(selection.focusNode))
        ) {
            this.activeSelection = this.makeSelection(selection, true);
        } else if (!this.activeSelection.anchorNode.isConnected) {
            this.activeSelection = this.makeSelection();
        }
        let { anchorNode, anchorOffset, focusNode, focusOffset, isCollapsed, direction } =
            this.activeSelection;

        // Transform the selection to return the depest possible node.
        if (deep) {
            [anchorNode, anchorOffset] = getDeepestPosition(anchorNode, anchorOffset);
            [focusNode, focusOffset] = isCollapsed
                ? [anchorNode, anchorOffset]
                : getDeepestPosition(focusNode, focusOffset);
        }
        let startContainer, startOffset, endContainer, endOffset;
        if (direction) {
            [startContainer, startOffset] = [anchorNode, anchorOffset];
            [endContainer, endOffset] = [focusNode, focusOffset];
        } else {
            [startContainer, startOffset] = [focusNode, focusOffset];
            [endContainer, endOffset] = [anchorNode, anchorOffset];
        }

        const range = new Range();
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
        {
            anchorNode,
            anchorOffset,
            focusNode = anchorNode,
            focusOffset = anchorOffset,
            inEditable = true,
        },
        { normalize = true } = {}
    ) {
        if (
            !this.editable.contains(anchorNode) ||
            !(anchorNode === focusNode || this.editable.contains(focusNode))
        ) {
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
        // @todo @phoenix: protect me! (selection could be nullish)
        if (selection && inEditable) {
            selection.setBaseAndExtent(anchorNode, anchorOffset, focusNode, focusOffset);
        }

        this.activeSelection = this.makeSelection(selection, true);
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
        const selection = this.getEditableSelection();
        const anchor = { node: selection.anchorNode, offset: selection.anchorOffset };
        const focus = { node: selection.focusNode, offset: selection.focusOffset };

        return {
            restore: () => {
                if (selection.inEditable) {
                    this.setSelection(
                        {
                            anchorNode: anchor.node,
                            anchorOffset: anchor.offset,
                            focusNode: focus.node,
                            focusOffset: focus.offset,
                        },
                        { normalize: false }
                    );
                }
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
        const selection = this.getEditableSelection();
        const range = new Range();
        range.setStart(selection.startContainer, selection.startOffset);
        range.setEnd(selection.endContainer, selection.endOffset);
        return [
            ...new Set(
                this.getTraversedNodes().flatMap((node) => {
                    const td = closestElement(node, ".o_selected_td");
                    if (td) {
                        return descendants(td);
                    } else if (
                        range.isPointInRange(node, 0) &&
                        range.isPointInRange(node, nodeSize(node))
                    ) {
                        return node;
                    } else {
                        return [];
                    }
                })
            ),
        ];
    }

    /**
     * Returns an array containing all the nodes traversed when walking the
     * selection.
     *
     * @returns {Node[]}
     */
    getTraversedNodes() {
        const selection = this.getEditableSelection({ deep: true });
        const selectedTableCells = this.editable.querySelectorAll(".o_selected_td");
        const document = this.editable.ownerDocument;
        const iterator = document.createNodeIterator(selection.commonAncestorContainer);
        let node;
        do {
            node = iterator.nextNode();
        } while (
            node &&
            node !== selection.startContainer &&
            !(selectedTableCells.length && node === selectedTableCells[0])
        );
        const traversedNodes = new Set([node, ...descendants(node)]);
        while (node && node !== selection.endContainer) {
            node = iterator.nextNode();
            if (node) {
                const selectedTable = closestElement(node, ".o_selected_table");
                if (selectedTable) {
                    for (const selectedTd of selectedTable.querySelectorAll(".o_selected_td")) {
                        traversedNodes.add(selectedTd);
                        descendants(selectedTd).forEach((descendant) =>
                            traversedNodes.add(descendant)
                        );
                    }
                } else {
                    // ignore edges nodes if they do not have content selected
                    if (
                        (node === selection.endContainer && selection.endOffset === 0) ||
                        (node === selection.startContainer &&
                            selection.startOffset === nodeSize(selection.startContainer))
                    ) {
                        continue;
                    }
                    traversedNodes.add(node);
                }
            }
        }
        return [...traversedNodes];
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
            this.activeSelection.anchorNode,
            this.activeSelection.anchorOffset,
            this.activeSelection.focusNode,
            this.activeSelection.focusOffset
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
    //     const selection = this.getEditableSelection({ deep: true });
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
                selection.inEditable &&
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
     *
     * @param {"backward"|"forward"} direction
     * @param {"character"|"word"|"line"} granularity
     * @returns {EditorSelection}
     */
    extendSelection(direction, granularity) {
        const editorSelection = this.getEditableSelection();
        if (!editorSelection.inEditable) {
            return editorSelection;
        }
        const selection = this.document.getSelection();
        // @todo @phoenix: protect me! (selection could be nullish)
        selection.modify("extend", direction, granularity);
        // @todo: check if it's still inside the editable
        this.activeSelection = this.makeSelection(selection, true);
        return this.activeSelection;
    }
}
