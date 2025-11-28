import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { renderToFragment } from "@web/core/utils/render";

export class NewsletterSubscribeCommonOptionPlugin extends Plugin {
    static id = "newsletterSubscribeCommonOption";
    resources = {
        dropzone_selector: [
            {
                selector: ".js_subscribe",
                dropNear: "p, h1, h2, h3, blockquote, .card",
                dropIn: ".row.o_grid_mode",
            },
        ],
        on_snippet_dropped_handlers: withSequence(-1, (args) => this.onSnippetDropped(args)),
    };

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_newsletter_aside")) {
            const sampleEl = snippetEl.querySelector("#checkbox_sample");
            if (sampleEl) {
                const mailingLists = await this.services.orm.searchRead(
                    "mailing.list",
                    [["is_public", "=", true]],
                    ["id", "name"],
                );
                if (mailingLists.length) {
                    const parentEl = sampleEl.parentElement;
                    sampleEl.remove();
                    const checkboxesFragment = renderToFragment(
                        "website_mass_mailing.NewsletterMailingListsCheckboxes", { mailingLists }
                    );
                    parentEl.append(...checkboxesFragment.children);
                } else {
                    sampleEl.closest(".s_website_form_field").remove();
                }
            }
        }
    }
}

registry
    .category("website-plugins")
    .add(NewsletterSubscribeCommonOptionPlugin.id, NewsletterSubscribeCommonOptionPlugin);
