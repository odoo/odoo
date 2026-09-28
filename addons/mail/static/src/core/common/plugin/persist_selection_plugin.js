import { Plugin } from "@html_editor/plugin";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { nodeSize } from "@html_editor/utils/position";

/**
 * @param {Node} root
 * @param {Node} node
 * @returns {number[]|undefined} indexes of the successive children leading from
 *  `root` to `node`, undefined if `node` is not inside `root`
 */
function getNodePath(root, node) {
    const path = [];
    while (node && node !== root) {
        path.unshift(childNodes(node.parentNode).indexOf(node));
        node = node.parentNode;
    }
    return node === root ? path : undefined;
}

/**
 * @param {Node} root
 * @param {number[]} path
 * @returns {Node|undefined}
 */
function getNodeFromPath(root, path) {
    let node = root;
    for (const index of path) {
        node = node?.childNodes[index];
    }
    return node;
}

/**
 * @typedef {Object} PersistedSelection
 * @property {number[]} anchorPath
 * @property {number} anchorOffset
 * @property {number[]} focusPath
 * @property {number} focusOffset
 */

/**
 * Persists the last selection set by the user, so that it can be restored when
 * the editor is re-created with the same content (e.g. when switching thread).
 *
 * The selection is saved as paths from the editable, so that it does not refer
 * to the nodes of an editor that no longer exists. Storing it, and discarding it
 * once it no longer matches the content, is up to the config.
 */
export class PersistSelectionPlugin extends Plugin {
    static id = "persistSelection";
    static dependencies = ["selection"];
    static shared = ["restore"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        on_selectionchange_handlers: ({ editableSelection, documentSelectionIsInEditable }) => {
            // The editable selection may be reset outside of it (e.g. editor
            // removed): keep the last one set by the user.
            if (documentSelectionIsInEditable) {
                this.save(editableSelection);
            }
        },
    };

    /** @param {import("@html_editor/core/selection_plugin").EditorSelection} selection */
    save({ anchorNode, anchorOffset, focusNode, focusOffset }) {
        const anchorPath = getNodePath(this.editable, anchorNode);
        const focusPath = getNodePath(this.editable, focusNode);
        if (!anchorPath || !focusPath) {
            return;
        }
        this.config.composerPluginDependencies.saveSelection({
            anchorPath,
            anchorOffset,
            focusPath,
            focusOffset,
        });
    }

    /**
     * @returns {boolean} whether the saved selection could be restored
     */
    restore() {
        /** @type {PersistedSelection|undefined} */
        const savedSelection = this.config.composerPluginDependencies.getSavedSelection();
        if (!savedSelection) {
            return false;
        }
        const anchorNode = getNodeFromPath(this.editable, savedSelection.anchorPath);
        const focusNode = getNodeFromPath(this.editable, savedSelection.focusPath);
        if (
            !anchorNode ||
            !focusNode ||
            savedSelection.anchorOffset > nodeSize(anchorNode) ||
            savedSelection.focusOffset > nodeSize(focusNode)
        ) {
            return false;
        }
        this.dependencies.selection.setSelection({
            anchorNode,
            anchorOffset: savedSelection.anchorOffset,
            focusNode,
            focusOffset: savedSelection.focusOffset,
        });
        return true;
    }
}
