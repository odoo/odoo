import { SnippetModel } from "@html_builder/snippets/snippet_service";
import { applyTextHighlight } from "@website/js/highlight_utils";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

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

    /**
     * @override
     */
    getSnippetLabel(snippetEl) {
        const label = super.getSnippetLabel(snippetEl);
        // Check if any element in the snippet has the "parallax" class to show
        // the "Parallax" label. This must be done this way because a theme or
        // custom snippet may add or remove parallax elements. Note that if a
        // label is already set, we do not change it.
        if (!label) {
            const contentEl = snippetEl.children[0];
            if (contentEl.matches(".parallax") || !!contentEl.querySelector(".parallax")) {
                return _t("Parallax");
            }
        }
        return label;
    },
});

registry
    .category("html_builder.snippetsPreprocessor")
    .add("website_snippets", (namespace, snippets) => {
        if (namespace === "website.snippets") {
            // This should be empty in master, it is used to fix snippets in stable.
        }
    });
