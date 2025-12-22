import { getDeepestPosition, isParagraphRelatedElement } from "@html_editor/utils/dom_info";
import { Plugin } from "../plugin";
import { isNotAllowedContent } from "./selection_plugin";
import { nodeSize } from "@html_editor/utils/position";

export class NoInlineRootPlugin extends Plugin {
    static id = "noInlineRoot";
    static dependencies = ["baseContainer", "selection", "history"];

    resources = {
        ...(!this.config.allowInlineAtRoot && {
            fix_selection_on_editable_root_handlers: this.fixSelectionOnEditableRoot.bind(this),
        }),
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
            this.preventNextPointerdownFix = false;
        });
    }

    /**
     * Places the cursor in a safe place (not the editable root).
     * Inserts an empty paragraph if selection results from mouse click and
     * there's no other way to insert text before/after a block.
     *
     * @param {Selection} selection - Collapsed selection at the editable root.
     */
    fixSelectionOnEditableRoot(selection) {
        if (
            !selection.isCollapsed ||
            selection.anchorNode !== this.editable ||
            this.config.allowInlineAtRoot
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
                this.dependencies.selection.setSelection({
                    anchorNode: anchorNode,
                    anchorOffset: 0,
                });
                return true;
            } else {
                this.dependencies.selection.resetActiveSelection();
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
                this.dependencies.selection.setSelection({
                    anchorNode: anchorNode,
                    anchorOffset: anchorOffset,
                });
                return true;
            } else {
                this.dependencies.selection.resetActiveSelection();
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
        if (nodeAfterCursor && isParagraphRelatedElement(nodeAfterCursor)) {
            // Cursor is right before a 'P'.
            this.dependencies.selection.setCursorStart(nodeAfterCursor);
            return true;
        } else if (nodeBeforeCursor && isParagraphRelatedElement(nodeBeforeCursor)) {
            // Cursor is right after a 'P'.
            this.dependencies.selection.setCursorEnd(nodeBeforeCursor);
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

            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            baseContainer.append(this.document.createElement("br"));
            if (!nodeAfterCursor) {
                // Cursor is at the end of the editable.
                this.editable.append(baseContainer);
            } else if (!nodeBeforeCursor) {
                // Cursor is at the beginning of the editable.
                this.editable.prepend(baseContainer);
            } else {
                // Cursor is between two non-p blocks
                nodeAfterCursor.before(baseContainer);
            }
            this.dependencies.selection.setCursorStart(baseContainer);
            this.dependencies.history.addStep();
            return true;
        }
        return false;
    }
}
