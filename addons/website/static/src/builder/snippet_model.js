import { applyTextHighlight } from "@website/js/highlight_utils";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { SnippetModel } from "@html_builder/snippets/snippet_service";

export class WebsiteSnippetModel extends SnippetModel {
    /**
     * @override
     */
    updateSnippetContent(snippetEl) {
        super.updateSnippetContent(...arguments);
        // Build the highlighted text content for new added snippets.
        for (const textEl of snippetEl?.querySelectorAll(".o_text_highlight") || []) {
            applyTextHighlight(textEl);
        }
    }

    /**
     * @override
     */
    getSnippetLabel(snippetEl) {
        const label = super.getSnippetLabel(snippetEl);
        // In the following test, we check whether labels should be displayed
        // depending on whether an option was applied or not. For example, a
        // snippet will have a “parallax” label if it was saved with the
        // parallax option enabled. On the other hand, it will not have this
        // label if the option was disabled before the snippet was saved.
        if (!label) {
            const contentEl = snippetEl.children[0];
            if (contentEl.matches(".parallax") || !!contentEl.querySelector(".parallax")) {
                return _t("Parallax");
            }
            if (contentEl.matches(".o_full_screen_height")) {
                return _t("Full-Screen");
            }
        }
        return label;
    }

    cleanSnippetForSave(snippetCopyEl, cleanForSaveHandlers) {
        const rootEl = snippetCopyEl.matches(".s_popup")
            ? snippetCopyEl.firstElementChild
            : snippetCopyEl;
        super.cleanSnippetForSave(rootEl, cleanForSaveHandlers);
    }

    getContext(snippetEl) {
        const context = super.getContext(...arguments);
        const editableParentEl = snippetEl.closest("[data-oe-model][data-oe-field][data-oe-id]");
        return Object.assign(context, {
            model: editableParentEl.dataset.oeModel,
            field: editableParentEl.dataset.oeField,
            resId: editableParentEl.dataset.oeId,
        });
    }
}

registry.category("html_builder.snippetsModel").add("website.snippets", WebsiteSnippetModel);

registry
    .category("html_builder.snippetsPreprocessor")
    .add("website_snippets", (namespace, snippets) => {
        if (namespace === "website.snippets") {
            // This should be empty in master, it is used to fix snippets in stable.
        }
    });
