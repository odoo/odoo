import { Plugin } from "@html_editor/plugin";
import { cleanTextNode } from "@html_editor/utils/dom";
import { isTextNode } from "@html_editor/utils/dom_info";
import { prepareUpdate } from "@html_editor/utils/dom_state";
import { descendants } from "@html_editor/utils/dom_traversal";
import { leftPos } from "@html_editor/utils/position";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";

/** @typedef {import("../core/selection_plugin").Cursors} Cursors */

/**
 * @typedef { Object } FeffShared
 * @property { FeffPlugin['addFeff'] } addFeff
 */

/**
 * This plugin manages the insertion and removal of the zero-width no-break
 * space character (U+FEFF). These characters enable the user to place the
 * cursor in positions that would otherwise not be easy or possible, such as
 * between two contenteditable=false elements, or at the end (but inside) of a
 * link.
 */
export class FeffPlugin extends Plugin {
    static id = "feff";
    static dependencies = ["selection"];
    static shared = ["addFeff"];

    resources = {
        normalize_handlers: this.updateFeffs.bind(this),
        clean_handlers: (root) => this.clean({ root, preserveSelection: true }),
        clean_for_save_handlers: this.clean.bind(this),
        intangible_char_for_keyboard_navigation_predicates: (ev, char, lastSkipped) =>
            // Skip first FEFF, but not the second one (unless shift is pressed).
            char === "\uFEFF" && (ev.shiftKey || lastSkipped !== "\uFEFF"),
    };

    clean({ root, preserveSelection = false }) {
        if (preserveSelection) {
            const cursors = this.getCursors();
            this.removeFeffs(root, cursors);
            cursors.restore();
        } else {
            this.removeFeffs(root, null);
        }
    }

    /**
     * @param {Element} root
     * @param {Cursors} [cursors]
     * @param {Object} [options]
     */
    removeFeffs(root, cursors, { exclude = () => false } = {}) {
        const hasFeff = (node) =>
            isTextNode(node) &&
            node.textContent.includes("\ufeff") &&
            node.parentElement.isContentEditable;

        for (const node of descendants(root).filter((n) => hasFeff(n) && !exclude(n))) {
            // Remove all FEFF within a `prepareUpdate` to make sure to make <br>
            // nodes visible if needed.
            const restoreSpaces = prepareUpdate(...leftPos(node));
            cleanTextNode(node, "\ufeff", cursors);
            restoreSpaces();
        }

        // Comment in the original code:
        //   We replace the text node with a new text node with the
        //   update text rather than just changing the text content of
        //   the node because these two methods create different
        //   mutations and at least the tour system breaks if all we
        //   send here is a text content change.
        // This is not done here as it breaks other plugins that rely on the
        // reference to the text node.
    }

    /**
     * @param {Element} element
     * @param {'before'|'after'|'prepend'|'append'} position
     * @param {Cursors} [cursors]
     * @returns {Node}
     */
    addFeff(element, position, cursors) {
        const feff = this.document.createTextNode("\ufeff");
        cursors?.update(callbacksForCursorUpdate[position](element, feff));
        element[position](feff);
        return feff;
    }

    updateFeffs(root) {
        const cursors = this.getCursors();
        // Each provider is responsible for adding (or keeping) FEFF nodes and
        // returning a list of them.
        const feffNodes = this.getResource("feff_providers").flatMap((p) => p(root, cursors));
        const feffNodesToKeep = new Set(feffNodes);
        this.removeFeffs(root, cursors, { exclude: (node) => feffNodesToKeep.has(node) });
        cursors.restore();
    }

    /**
     * Retuns a patched version of cursors in which `restore` does nothing
     * unless `update` has been called at least once.
     */
    getCursors() {
        const cursors = this.dependencies.selection.preserveSelection();
        const originalUpdate = cursors.update.bind(cursors);
        const originalRestore = cursors.restore.bind(cursors);
        let shouldRestore = false;
        cursors.update = (...args) => {
            shouldRestore = true;
            return originalUpdate(...args);
        };
        cursors.restore = () => {
            if (shouldRestore) {
                originalRestore();
            }
        };
        return cursors;
    }
}
