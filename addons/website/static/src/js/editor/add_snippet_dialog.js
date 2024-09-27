import { AddSnippetDialog } from "@web_editor/js/editor/add_snippet_dialog";
import { patch } from "@web/core/utils/patch";
import { applyTextHighlight } from "@website/js/text_processing";

patch(AddSnippetDialog.prototype, {
    /**
     * Build the highlighted text for the snippets preview.
     *
     * @override
     */
    async insertSnippets() {
        await super.insertSnippets();
        for (const textEl of this.iframeDocument?.querySelectorAll(".o_text_highlight") || []) {
            applyTextHighlight(textEl);
        }
    },
});
