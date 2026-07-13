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
        fix_selection_on_no_inline_root_overrides: this.fixSelectionOnNoInlineRoot.bind(this),
        is_no_inline_root_predicates: (node) => {
            if (node === this.editable) {
                return true;
            }
        },
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
     * Places the cursor in a safe place (not the editable root, nor any
     * other registered no-inline root).
     *
     * @param {import("./selection_plugin").EditorSelection} selection
     * @returns {boolean} Whether the selection was fixed
     */
    fixSelectionOnNoInlineRoot(selection) {
        const { anchorNode, anchorOffset } = selection;

        const root = anchorNode;
        const children = childNodes(root);
        const nodeAfterCursor = children[anchorOffset];
        const nodeBeforeCursor = children[anchorOffset - 1];
        const key = this.currentKeyDown;
        delete this.currentKeyDown;

        if (key?.startsWith("Arrow")) {
            return this.fixSelectionOnNoInlineRootArrowKeys(
                root,
                nodeAfterCursor,
                nodeBeforeCursor,
                key
            );
        }
        return this.fixSelectionOnNoInlineRootGeneric(
            root,
            nodeAfterCursor,
            nodeBeforeCursor,
            anchorOffset
        );
    }
    /**
     * @param {Node} root
     * @param {Node} nodeAfterCursor
     * @param {Node} nodeBeforeCursor
     * @param {string} key
     * @returns {boolean} Whether the selection was fixed
     */
    fixSelectionOnNoInlineRootArrowKeys(root, nodeAfterCursor, nodeBeforeCursor, key) {
        if (!["ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown"].includes(key)) {
            return false;
        }
        const directionForward = ["ArrowRight", "ArrowDown"].includes(key);
        let node = directionForward ? nodeAfterCursor : nodeBeforeCursor;
        if (!node && root !== this.editable) {
            // The root has no child in that direction (e.g. a table wrapper).
            // Continue the navigation using its sibling in the parent container.
            node = directionForward ? root.nextElementSibling : root.previousElementSibling;
        }
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
     * @param {Node} root
     * @param {Node} nodeAfterCursor
     * @param {Node} nodeBeforeCursor
     * @param {number} offset Offset of the cursor in the root.
     * @returns {boolean} Whether the selection was fixed
     */
    fixSelectionOnNoInlineRootGeneric(root, nodeAfterCursor, nodeBeforeCursor, offset) {
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
        if (root === this.editable) {
            return false;
        }
        // Neither direct child works (e.g. table wrapper only holds a table),
        // fall back to the root's own sibling on the cursor's side instead.
        const atStart = offset === 0;
        const sibling = atStart ? root.previousElementSibling : root.nextElementSibling;
        if (isParagraphRelatedElement(sibling)) {
            this.dependencies.selection[atStart ? "setCursorEnd" : "setCursorStart"](sibling);
            return true;
        }
        return false;
    }
}
