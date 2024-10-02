import { AddSnippetDialog } from "@web_editor/js/editor/add_snippet_dialog";
import { patch } from "@web/core/utils/patch";
import { applyTextHighlight } from "@website/js/text_processing";

patch(AddSnippetDialog.prototype, {
    /**
     * @override
     */
    _updateSnippetContent(targetEl) {
        super._updateSnippetContent(...arguments);
        // Build the highlighted text content for the snippets.
        for (const textEl of targetEl?.querySelectorAll(".o_text_highlight") || []) {
            applyTextHighlight(textEl);
        }
    },
});
