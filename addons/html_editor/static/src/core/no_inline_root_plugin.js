import {
    allowsParagraphRelatedElements,
    getDeepestPosition,
    isEditionBoundary,
    isParagraphRelatedElement,
    isPhrasingContent,
} from "@html_editor/utils/dom_info";
import { Plugin } from "../plugin";
import { isNotAllowedContent } from "./selection_plugin";
import { endPos, startPos } from "@html_editor/utils/position";
import { childNodes, getConnectedParents } from "@html_editor/utils/dom_traversal";

// These elements should only have inline content (even if they have a `block`
// display style, for example if they are in a flex)
// NOTE: h1, h2, ..., p, pre already prevents wrapping their children into block
const ONLY_ALLOW_INLINE_TAGS = new Set([
    ...["a", "em", "strong", "small", "s", "cite", "q", "abbr", "data", "time", "code"],
    ...["samp", "sub", "sup", "i", "b", "u", "mark", "bdi", "span", "label", "button"],
]);

/**
 * @typedef {((el: HTMLElement) => boolean | void)[]} are_inlines_allowed_at_root_predicates
 */
export class NoInlineRootPlugin extends Plugin {
    static id = "noInlineRoot";
    static dependencies = ["baseContainer", "selection", "history", "dom"];

    /** @type {import("plugins").EditorResources} */
    resources = {
        fix_selection_on_editable_root_overrides: this.fixSelectionOnEditableRoot.bind(this),
        on_inserted_handlers: this.onInserted.bind(this),
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
     * Return true if inlines are allowed at root, false otherwise.
     *
     * @param {Node} node
     * @returns {boolean}
     */
    areInlinesAllowedAtRoot(node) {
        if (ONLY_ALLOW_INLINE_TAGS.has(node.tagName.toLowerCase())) {
            return true;
        }
        return (
            ONLY_ALLOW_INLINE_TAGS.has(node.tagName.toLowerCase()) ||
            (this.checkPredicates("are_inlines_allowed_at_root_predicates", node) ??
                this.config.allowInlineAtRoot)
        );
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
    /**
     * When insertion produced inline siblings in places where inline content is
     * not allowed, wrap them into base containers.
     *
     * @param {Node[]} insertedNodes
     */
    onInserted(insertedNodes) {
        for (const parent of getConnectedParents(insertedNodes)) {
            if (
                !this.areInlinesAllowedAtRoot(parent) &&
                isEditionBoundary(parent, this.editable) &&
                allowsParagraphRelatedElements(parent) &&
                !isPhrasingContent(parent)
            ) {
                // Ensure that edition boundaries do not have inline content.
                this.dependencies.dom.wrapInlinesInBlocks(parent, {
                    baseContainerNodeName: this.dependencies.baseContainer.getDefaultNodeName(),
                });
            }
        }
    }
}
