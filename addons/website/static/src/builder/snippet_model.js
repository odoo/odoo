import { SnippetModel } from "@html_builder/snippets/snippet_service";
import { applyTextHighlight } from "@website/js/highlight_utils";
import { registry } from "@web/core/registry";
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

registry
    .category("html_builder.snippetsPreprocessor")
    .add("website_snippets", (namespace, snippets) => {
        if (namespace === "website.snippets") {
            // This should be empty in master, it is used to fix snippets in stable.

            // TODO remove in master: add s_progress_bar_text in progress bar where it's missing, fix the previous wrong width
            const progressBarEls = snippets.querySelectorAll(".progress-bar");
            progressBarEls.forEach((el) => {
                if (el.style.width === "45%") {
                    el.style.width = "25%";
                }
                if (!el.querySelector(".s_progress_bar_text")) {
                    const textEl = document.createElement("span");
                    textEl.classList.add("s_progress_bar_text", "small");
                    textEl.textContent = el.style.width;
                    if (el.closest(".s_progress_bar_label_hidden")) {
                        textEl.classList.add("d-none");
                    }
                    el.appendChild(textEl);
                }
            });
        }
    });
