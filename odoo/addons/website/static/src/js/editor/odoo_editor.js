/** @odoo-module **/

import { OdooEditor } from "@web_editor/js/editor/odoo-editor/src/OdooEditor";
import { patch } from "@web/core/utils/patch";
import { removeTextHighlight } from "@website/js/text_processing";

/**
 * The goal of this patch is to correctly handle OdooEditor's behaviour for text
 * highlight elements.
 */
patch(OdooEditor.prototype, {
    /**
     * @override
     */
    _onClipboardCopy(e) {
        super._onClipboardCopy(e);

        const selection = this.document.getSelection();
        const range = selection.getRangeAt(0);
        let rangeContent = range.cloneContents();
        const firstChild = rangeContent.firstChild;

        // Fix the copied range and remove the highlight units when the content
        // is partially selected.
        if (firstChild && firstChild.className && firstChild.className.includes("o_text_highlight_item")) {
            const textHighlightEl = range.commonAncestorContainer.cloneNode();
            textHighlightEl.replaceChildren(...rangeContent.childNodes);
            removeTextHighlight(textHighlightEl);
            rangeContent = textHighlightEl;
            const data = document.createElement("data");
            data.append(rangeContent);
            const html = data.innerHTML;
            e.clipboardData.setData("text/plain", selection.toString());
            e.clipboardData.setData("text/html", html);
            e.clipboardData.setData("text/odoo-editor", html);
        }
    },
});
