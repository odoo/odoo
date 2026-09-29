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
/* eslint-disable */
const ONLY_ALLOW_INLINE_TAGS = new Set([
    "a", "em", "strong", "small", "s", "cite", "q", "abbr", "data", "time", "code",
    "samp", "sub", "sup", "i", "b", "u", "mark", "bdi", "span", "label", "button",
]);
/* eslint-enable */

/**
 * @typedef {((el: HTMLElement) => boolean | void)[]} are_inlines_allowed_at_root_predicates
 */
export class NoInlineRootPlugin extends Plugin {
    static id = "noInlineRoot";
    static dependencies = ["baseContainer", "selection", "history", "dom"];

    /** @type {import("plugins").EditorResources} */
    resources = {
        fix_selection_on_no_inline_root_overrides: this.fixSelectionOnNoInlineRoot.bind(this),
        is_no_inline_root_predicates: (node) => {
            if (node === this.editable) {
                return true;
            }
        },
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
        return this.fixSelectionOnNoInlineRootGeneric(root, nodeAfterCursor, nodeBeforeCursor);
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
            // Nothing to hand the cursor over to, the editable root always has
            // selection placeholders around its blockers, any other root may
            // have none, so it gets a base container to place a cursor there.
            return root === this.editable
                ? false
                : this.insertBaseContainerNextTo(root, !directionForward);
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
     * @returns {boolean} Whether the selection was fixed
     */
    fixSelectionOnNoInlineRootGeneric(root, nodeAfterCursor, nodeBeforeCursor) {
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
        const atStart = !nodeBeforeCursor;
        const sibling = atStart ? root.previousElementSibling : root.nextElementSibling;
        if (isParagraphRelatedElement(sibling)) {
            this.dependencies.selection[atStart ? "setCursorEnd" : "setCursorStart"](sibling);
            return true;
        }
        // Only a click is a clear enough intent to add content to the document.
        return this.isPointerDown ? this.insertBaseContainerNextTo(root, atStart) : false;
    }

    /**
     * Insert an empty base container next to the given root and place the
     * cursor in it. Last resort for a root that holds no valid position and
     * has no sibling able to take the cursor, like a table wrapper standing
     * alone in its parent.
     *
     * @param {HTMLElement} root
     * @param {boolean} before Whether to insert it before the root.
     * @returns {boolean} Whether the selection was fixed
     */
    insertBaseContainerNextTo(root, before) {
        const baseContainer = this.dependencies.baseContainer.createBaseContainer();
        root[before ? "before" : "after"](baseContainer);
        this.dependencies.selection.setCursorStart(baseContainer);
        this.dependencies.history.commit();
        return true;
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
