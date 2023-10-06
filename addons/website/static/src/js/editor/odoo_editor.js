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
    /**
     * @override
     */
    execCommand() {
        const sel = this.document.getSelection();
        const range = sel.getRangeAt(0);
        const startContainer = range.startContainer;
        const textEl = (startContainer.nodeType === Node.ELEMENT_NODE ?
            startContainer : startContainer.parentElement).closest(".o_text_highlight");
        if (textEl) {
            // In the same way as for `oEnter()`, some other editor commands
            // may lead to split the content of text highlight lines. We need to
            // keep track of them to make sure the update is done correctly.
            [...textEl.querySelectorAll(".o_text_highlight_item")].forEach(line => {
                line.classList.add("o_text_highlight_item_dirty");
            });
        }
        return super.execCommand(...arguments);
    }
});
