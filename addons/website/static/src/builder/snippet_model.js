import { SnippetModel } from "@html_builder/snippets/snippet_service";
import { applyTextHighlight } from "@website/js/highlight_utils";
import { patch } from "@web/core/utils/patch";

patch(SnippetModel.prototype, {
    /**
     * @override
     */
    updateSnippetContent(snippetEl) {
        super.updateSnippetContent(...arguments);
        // Build the highlighted text content for new added snippets.
        for (const textEl of snippetEl?.querySelectorAll(".o_text_highlight") || []) {
            applyTextHighlight(textEl);
        }
    },
});
