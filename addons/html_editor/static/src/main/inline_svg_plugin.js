import { Plugin } from "../plugin";
import { closestSvgRoot, isContentEditable, isZwnbsp } from "../utils/dom_info";
import { closestElement, selectElements } from "../utils/dom_traversal";
import { DISABLED_NAMESPACE } from "./toolbar/toolbar_plugin";

/**
 * Inline SVGs are edited as a whole, except for the text of their `<text>`
 * elements (see `isContentEditable`).
 *
 * A text of an SVG cannot contain HTML elements: it cannot be split into blocks
 * nor contain line breaks, tabs or formatting.
 */
export class InlineSvgPlugin extends Plugin {
    static id = "inlineSvg";
    static dependencies = ["feff", "selection"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        split_element_block_overrides: ({ targetNode }) => !!closestSvgRoot(targetNode),
        insert_line_break_element_overrides: ({ targetNode }) => !!closestSvgRoot(targetNode),
        tab_overrides: () => this.isSelectionInSvg(),
        shift_tab_overrides: () => this.isSelectionInSvg(),
        properties: {
            predicate: (node) => !!closestSvgRoot(node),
            formattable: false,
            powerbox: false,
            toolbar: DISABLED_NAMESPACE,
        },
        // Without a text node, the cursor cannot be put in an empty text: the
        // browser would insert typed text after the SVG.
        feff_providers: (root, cursors) =>
            selectElements(root, "svg text")
                .filter((textEl) => this.isEmptyText(textEl) && isContentEditable(textEl))
                .map((textEl) => this.getFeff(textEl, cursors)),
        // E.g. when typing over a selected text: the selection is deleted, then
        // the browser inserts the typed text.
        on_deleted_handlers: () => {
            const { anchorNode } = this.dependencies.selection.getEditableSelection();
            const textEl = closestSvgRoot(anchorNode) && closestElement(anchorNode, "text");
            if (textEl && this.isEmptyText(textEl)) {
                const feff = this.getFeff(textEl);
                this.dependencies.selection.setSelection({ anchorNode: feff, anchorOffset: 0 });
            }
        },
    };

    isSelectionInSvg() {
        const { anchorNode } = this.dependencies.selection.getEditableSelection();
        return !!closestSvgRoot(anchorNode);
    }

    /**
     * @param {SVGTextElement} textEl
     * @returns {boolean}
     */
    isEmptyText(textEl) {
        return !textEl.textContent.replaceAll("﻿", "");
    }

    /**
     * @param {SVGTextElement} textEl
     * @param {import("@html_editor/core/selection_plugin").Cursors} [cursors]
     * @returns {Text} the FEFF of the empty text (added if needed)
     */
    getFeff(textEl, cursors) {
        return (
            [...textEl.childNodes].find(isZwnbsp) ??
            this.dependencies.feff.addFeff(textEl, "append", cursors)
        );
    }
}
