import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { WebsiteSnippetViewer } from "@website/builder/snippet_viewer";

export class WebsiteSnippetsPlugin extends Plugin {
    static id = "website_snippets";
    resources = {
        snippet_viewer_per_template: {
            templateKey: "website.snippets",
            component: WebsiteSnippetViewer,
        },
        update_snippet_content: (snippetEl) => {
            // Build the highlighted text content for new added snippets.
            for (const textEl of snippetEl?.querySelectorAll(".o_text_highlight") || []) {
                applyTextHighlight(textEl);
            }
        },
    };
}
