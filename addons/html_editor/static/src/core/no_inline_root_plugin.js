import { getDeepestPosition, isParagraphRelatedElement } from "@html_editor/utils/dom_info";
import { Plugin } from "../plugin";
import { isNotAllowedContent } from "./selection_plugin";
import { endPos, startPos } from "@html_editor/utils/position";
import { childNodes } from "@html_editor/utils/dom_traversal";

export class NoInlineRootPlugin extends Plugin {
    static id = "noInlineRoot";
    static dependencies = ["baseContainer", "selection", "history"];

    /** @type {import("plugins").EditorResources} */
    resources = {
        fix_selection_on_editable_root_overrides: this.fixSelectionOnEditableRoot.bind(this),
    };

    setup() {
        this.addDomListener(this.editable, "keydown", (ev) => {
            this.currentKeyDown = ev.key;
        });
        this.addDomListener(this.editable, "pointerdown", () => {
            this.isPointerDown = true;
        });
        this.addDomListener(this.editable, "pointerup", () => {
            this.isPointerDown = false;
        });
    }

    /**
     * Places the cursor in a safe place (not the editable root).
     * Inserts an empty paragraph if selection results from mouse click and
     * there's no other way to insert text before/after a block.
     *
     * @param {import("./selection_plugin").EditorSelection} selection
     * @returns {boolean} Whether the selection was fixed
     */
    fixSelectionOnEditableRoot(selection) {
        if (!selection.isCollapsed || selection.anchorNode !== this.editable) {
            return false;
        }

        const children = childNodes(this.editable);
        const nodeAfterCursor = children[selection.anchorOffset];
        const nodeBeforeCursor = children[selection.anchorOffset - 1];
        const key = this.currentKeyDown;
        delete this.currentKeyDown;

        if (key?.startsWith("Arrow")) {
            return this.fixSelectionOnEditableRootArrowKeys(nodeAfterCursor, nodeBeforeCursor, key);
        }
        return this.fixSelectionOnEditableRootGeneric(nodeAfterCursor, nodeBeforeCursor);
    }
    /**
     * @param {Node} nodeAfterCursor
     * @param {Node} nodeBeforeCursor
     * @param {string} key
     * @returns {boolean} Whether the selection was fixed
     */
    fixSelectionOnEditableRootArrowKeys(nodeAfterCursor, nodeBeforeCursor, key) {
        if (!["ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown"].includes(key)) {
            return false;
        }
        const directionForward = ["ArrowRight", "ArrowDown"].includes(key);
        let node = directionForward ? nodeAfterCursor : nodeBeforeCursor;
        while (node && isNotAllowedContent(node)) {
            node = directionForward ? node.nextElementSibling : node.previousElementSibling;
        }
        if (!node) {
            return false;
        }
        let [anchorNode, anchorOffset] = directionForward ? startPos(node) : endPos(node);
        [anchorNode, anchorOffset] = getDeepestPosition(anchorNode, anchorOffset);
        this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        return true;
    }
    /**
     * @param {Node} nodeAfterCursor
     * @param {Node} nodeBeforeCursor
     * @returns {boolean} Whether the selection was fixed
     */
    fixSelectionOnEditableRootGeneric(nodeAfterCursor, nodeBeforeCursor) {
        if (isParagraphRelatedElement(nodeAfterCursor)) {
            // Cursor is right before a 'P'.
            this.dependencies.selection.setCursorStart(nodeAfterCursor);
            return true;
        }
        if (isParagraphRelatedElement(nodeBeforeCursor)) {
            // Cursor is right after a 'P'.
            this.dependencies.selection.setCursorEnd(nodeBeforeCursor);
            return true;
        }
        return false;
    }
}
