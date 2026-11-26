import { Plugin } from "../plugin";
import { closestSvgRoot, isContentEditable, isZwnbsp } from "../utils/dom_info";
import { closestElement, selectElements } from "../utils/dom_traversal";
import { leftPos, rightPos } from "../utils/position";
import { DISABLED_NAMESPACE } from "./toolbar/toolbar_plugin";

/**
 * Inline SVGs are edited as a whole, except for the text of their `<text>`
 * elements (see `isContentEditable`).
 *
 * A text of an SVG cannot contain HTML elements: it cannot be split into blocks
 * nor contain line breaks, tabs or formatting. Enter and Tab are used to go from
 * one text to another instead, as in a form.
 */
export class InlineSvgPlugin extends Plugin {
    static id = "inlineSvg";
    static dependencies = ["feff", "selection"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        split_element_block_overrides: this.handleSplitInSvg.bind(this),
        insert_line_break_element_overrides: ({ targetNode }) => !!closestSvgRoot(targetNode),
        tab_overrides: () => this.selectSiblingText("next"),
        shift_tab_overrides: () => this.selectSiblingText("previous"),
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

    /**
     * At the end of a text, Enter moves the cursor to the start of the next
     * text of the SVG, or right after the SVG if there is none. Elsewhere in
     * the SVG, it does nothing.
     *
     * @param {Object} params
     * @param {Node} params.targetNode
     * @param {number} params.targetOffset
     * @returns {boolean} whether the split was handled
     */
    handleSplitInSvg({ targetNode, targetOffset }) {
        const svg = closestSvgRoot(targetNode);
        if (!svg) {
            return false;
        }
        const textEl = closestElement(targetNode, "text");
        if (textEl && this.isAtTextEnd(textEl, targetNode, targetOffset)) {
            const nextTextEl = this.getSiblingText(svg, textEl, "next");
            if (nextTextEl) {
                this.dependencies.selection.setCursorStart(nextTextEl);
            } else {
                const [anchorNode, anchorOffset] = rightPos(svg);
                this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
            }
        }
        return true;
    }

    /**
     * Tab and Shift+Tab select the content of the next or previous text of
     * the SVG, so that typing replaces it. From the last or first text, they
     * move the cursor right after or right before the SVG.
     *
     * @param {"next"|"previous"} direction
     * @returns {boolean} whether the selection is in an SVG
     */
    selectSiblingText(direction) {
        const { anchorNode } = this.dependencies.selection.getEditableSelection();
        const svg = closestSvgRoot(anchorNode);
        if (!svg) {
            return false;
        }
        const textEl = closestElement(anchorNode, "text");
        const siblingTextEl = textEl && this.getSiblingText(svg, textEl, direction);
        if (siblingTextEl) {
            this.dependencies.selection.setSelection({
                anchorNode: siblingTextEl,
                anchorOffset: 0,
                focusNode: siblingTextEl,
                focusOffset: siblingTextEl.childNodes.length,
            });
        } else if (textEl) {
            const [anchorNode, anchorOffset] = (direction === "next" ? rightPos : leftPos)(svg);
            this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        }
        return true;
    }

    /**
     * @param {SVGSVGElement} svg
     * @param {SVGTextElement} textEl
     * @param {"next"|"previous"} direction
     * @returns {SVGTextElement|undefined}
     */
    getSiblingText(svg, textEl, direction) {
        const texts = [...svg.querySelectorAll("text")];
        return texts[texts.indexOf(textEl) + (direction === "next" ? 1 : -1)];
    }

    /**
     * @param {SVGTextElement} textEl
     * @param {Node} node
     * @param {number} offset
     * @returns {boolean} whether there is no visible text after the position
     */
    isAtTextEnd(textEl, node, offset) {
        const range = this.document.createRange();
        range.setStart(node, offset);
        range.setEnd(textEl, textEl.childNodes.length);
        return !range.toString().replaceAll("\ufeff", "");
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
