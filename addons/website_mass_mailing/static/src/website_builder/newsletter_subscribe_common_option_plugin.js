import { before, SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";
import { POPUP } from "@website/builder/plugins/options/popup_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { renderToFragment } from "@web/core/utils/render";
import { NewsletterSubscribeCommonOption } from "./newsletter_subscribe_common_option";

export const NEWSLETTER_SELECT = before(POPUP);

class NewsletterSubscribeCommonOptionPlugin extends Plugin {
    static id = "newsletterSubscribeCommonOption";
    static dependencies = ["mailingListSubscribeOption", "recaptchaSubscribeOption"];
    resources = {
        builder_options: [
            withSequence(NEWSLETTER_SELECT, {
                OptionComponent: NewsletterSubscribeCommonOption,
                props: this.getProps(),
                selector: ".s_newsletter_list",
                exclude: [
                    ".s_newsletter_block .s_newsletter_list",
                    ".o_newsletter_popup .s_newsletter_list",
                    ".s_newsletter_box .s_newsletter_list",
                    ".s_newsletter_centered .s_newsletter_list",
                    ".s_newsletter_grid .s_newsletter_list",
                    ".s_newsletter_aside .s_newsletter_list",
                ].join(", "),
            }),
            withSequence(NEWSLETTER_SELECT, {
                OptionComponent: NewsletterSubscribeCommonOption,
                props: this.getProps(),
                selector: ".o_newsletter_popup",
                applyTo: ".s_newsletter_list",
            }),
            withSequence(SNIPPET_SPECIFIC, {
                template: "website_mass_mailing.MailingListSubscribeFormOption",
                selector: ".s_newsletter_subscribe_form",
            }),
        ],
        dropzone_selector: [
            {
                selector: ".js_subscribe",
                dropNear: "p, h1, h2, h3, blockquote, .card",
                dropIn: ".row.o_grid_mode",
            },
        ],
        on_snippet_dropped_handlers: withSequence(-1, (args) => this.onSnippetDropped(args)),
    };

    getProps() {
        return {
            fetchMailingLists: this.dependencies.mailingListSubscribeOption.fetchMailingLists,
            hasRecaptcha: this.dependencies.recaptchaSubscribeOption.hasRecaptcha,
        };
    }

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
