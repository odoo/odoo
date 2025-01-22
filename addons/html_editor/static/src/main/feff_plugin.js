import { Plugin } from "@html_editor/plugin";
import { cleanTextNode } from "@html_editor/utils/dom";
import { isTextNode, isZwnbsp } from "@html_editor/utils/dom_info";
import { prepareUpdate } from "@html_editor/utils/dom_state";
import { descendants, selectElements } from "@html_editor/utils/dom_traversal";
import { leftPos } from "@html_editor/utils/position";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";

/** @typedef {import("../core/selection_plugin").Cursors} Cursors */

/**
 * @typedef { Object } FeffShared
 * @property { FeffPlugin['addFeff'] } addFeff
 * @property { FeffPlugin['removeFeffs'] } removeFeffs
 * @property { FeffPlugin['updateFeffs'] } updateFeffs
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
    static shared = ["addFeff", "removeFeffs", "updateFeffs"];

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

    /**
     * Adds a FEFF before and after each element that matches the selectors
     * provided by the registered providers.
     *
     * @param {Element} root
     * @param {Cursors} cursors
     * @returns {Node[]}
     */
    padWithFeffs(root, cursors) {
        const combinedSelector = this.getResource("selectors_for_feff_providers")
            .map((provider) => provider())
            .join(", ");
        if (!combinedSelector) {
            return [];
        }
        const elements = [...selectElements(root, combinedSelector)];
        const feffNodes = elements
            .flatMap((el) => {
                const addFeff = (position) => this.addFeff(el, position, cursors);
                return [
                    isZwnbsp(el.previousSibling) ? el.previousSibling : addFeff("before"),
                    isZwnbsp(el.nextSibling) ? el.nextSibling : addFeff("after"),
                ];
            })
            // Avoid sequential FEFFs
            .filter((feff, i, array) => !(i > 0 && areCloseSiblings(array[i - 1], feff)));
        return feffNodes;
    }

    updateFeffs(root) {
        const cursors = this.getCursors();
        // Pad based on selectors
        const feffNodesBasedOnSelectors = this.padWithFeffs(root, cursors);
        // Custom feff adding
        // Each provider is responsible for adding (or keeping) FEFF nodes and
        // returning a list of them.
        const customFeffNodes = this.getResource("feff_providers").flatMap((p) => p(root, cursors));
        const feffNodesToKeep = new Set([...feffNodesBasedOnSelectors, ...customFeffNodes]);
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

/**
 * Whether two nodes are consecutive siblings, ignoring empty text nodes between
 * them.
 *
 * @param {Node} a
 * @param {Node} b
 */
function areCloseSiblings(a, b) {
    let next = a.nextSibling;
    // skip empty text nodes
    while (next && isTextNode(next) && !next.textContent) {
        next = next.nextSibling;
    }
    return next === b;
}
