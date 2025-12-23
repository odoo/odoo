import { before, SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";
import { POPUP } from "@website/builder/plugins/options/popup_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { NewsletterSubscribeCommonOption, NewsletterSubscribeCommonPopupOption } from "./newsletter_subscribe_common_option";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { renderToFragment } from "@web/core/utils/render";

export const NEWSLETTER_SELECT = before(POPUP);

export class MailingListSubscribeFormOption extends BaseOptionComponent {
    static template = "website_mass_mailing.MailingListSubscribeFormOption";
    static selector = ".s_newsletter_subscribe_form";
}

class NewsletterSubscribeCommonOptionPlugin extends Plugin {
    static id = "newsletterSubscribeCommonOption";
    resources = {
        builder_options: [
            withSequence(NEWSLETTER_SELECT, NewsletterSubscribeCommonOption),
            withSequence(NEWSLETTER_SELECT, NewsletterSubscribeCommonPopupOption),
            withSequence(SNIPPET_SPECIFIC, MailingListSubscribeFormOption),
        ],
        dropzone_selector: [
            {
                selector: ".js_subscribe",
                dropNear: "p, h1, h2, h3, blockquote, .card",
                dropIn: ".row.o_grid_mode",
            },
        ],
        on_snippet_dropped_handlers: withSequence(-1, (args) => this.onSnippetDropped(args)),
        is_unremovable_selector: ".js_subscribe_btn",
        immutable_link_selectors: [".js_subscribe_btn"],
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
