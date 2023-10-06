/** @odoo-module **/

// The goal of this patch is to handle some website-specific behavior when
// executing editor commands on DOM elements.
import { UNMERGEABLE_SELECTORS } from "@web_editor/js/editor/odoo-editor/src/utils/sanitize";

UNMERGEABLE_SELECTORS.push("o_text_highlight_item");

/**
 * Used to keep track of duplicated text highlight elements after content
 * split. The `o_text_highlight_item_dirty` class will be automatically removed
 * after the highlight adjustment.
 */
Text.prototype.oEnterOdooEditor = Text.prototype.oEnter;
Text.prototype.oEnter = function (offset) {
    if (this.parentElement?.classList.contains("o_text_highlight_item")) {
        this.parentElement.classList.add("o_text_highlight_item_dirty");
    }
    this.oEnterOdooEditor(...arguments);
};

/**
 * Used to prevent handling the text highlight SVG the same way as text
 * content on backward deletion.
 */
HTMLElement.prototype.oDeleteBackwardOdooEditor = HTMLElement.prototype.oDeleteBackward;
HTMLElement.prototype.oDeleteBackward = function (offset, alreadyMoved = false, offsetLimit) {
    const leftNode = this.childNodes[offset - 1];
    if (offset && leftNode) {
        // Some elements like text highlight SVGs should be ignored.
        if (leftNode.classList && leftNode.classList.contains("o_text_highlight_svg")) {
            return;
        }
    }
    this.oDeleteBackwardOdooEditor(...arguments);
};
