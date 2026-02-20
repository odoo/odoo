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
<<<<<<< 9ace7274501c62d551efd78273ad9b62c1b354e0
    getSnippetLabel(snippetEl) {
        const label = super.getSnippetLabel(snippetEl);
        // In the following test, we check whether labels should be displayed
        // depending on whether an option was applied or not. For example, a
        // snippet will have a “parallax” label if it was saved with the
        // parallax option enabled. On the other hand, it will not have this
        // label if the option was disabled before the snippet was saved.
        if (!label) {
||||||| 6f9d5ca558ed1de5a95d60e84f01d2c9dbbac5e3
    getSnippetLabel(snippetEl) {
        let label = super.getSnippetLabel(snippetEl);
        // Check if any element in the snippet has the "parallax" class to show
        // the "Parallax" label. This must be done this way because a theme or
        // custom snippet may add or remove parallax elements. Note that if a
        // label is already set, we do not change it.
        // TODO In master, remove the "|| label === 'Parallax'" part from the
        // condition, as the label="Parallax" will be removed from the snippet
        // definition.
        if (!label || label === "Parallax") {
            label = "";
=======
    getSnippetLabel(snippetEl, isCustom = false) {
        let label = super.getSnippetLabel(snippetEl);
        if (!label) {
>>>>>>> e4d882796488784bbff879f5d6f7e49a1c818d38
            const contentEl = snippetEl.children[0];
            const parallaxLabel = _t("Parallax");
            // Retrieve the original snippet label when a snippet is a custom
            // snippet.
            if (isCustom) {
                const originalSnippetLabel = this.getOriginalSnippet(
                    contentEl.dataset.snippet
                )?.label;
                if (originalSnippetLabel && originalSnippetLabel !== parallaxLabel) {
                    label = originalSnippetLabel;
                }
            }
            // Check if any element in the snippet has the "parallax" class to
            // show the "Parallax" label. This must be done this way because a
            // theme or custom snippet may add or remove parallax elements. Note
            // that if a label is already set, we do not change it.
            if (
                !label &&
                (contentEl.matches(".parallax") || !!contentEl.querySelector(".parallax"))
            ) {
                label = parallaxLabel;
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
