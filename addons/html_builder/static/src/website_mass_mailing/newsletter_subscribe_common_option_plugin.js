import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { NewsletterSubscribeCommonOption } from "./newsletter_subscribe_common_option";

class NewsletterSubscribeCommonOptionPlugin extends Plugin {
    static id = "newsletterSubscribeCommonOption";
    static dependencies = ["mailingListSubscribeOption", "recaptchaSubscribeOption"];
    resources = {
        builder_options: [
            {
                OptionComponent: NewsletterSubscribeCommonOption,
                props: this.getProps(),
                selector: ".s_newsletter_list",
                exclude: [
                    ".s_newsletter_block .s_newsletter_list",
                    ".o_newsletter_popup .s_newsletter_list",
                    ".s_newsletter_box .s_newsletter_list",
                    ".s_newsletter_centered .s_newsletter_list",
                    ".s_newsletter_grid .s_newsletter_list",
                ].join(", "),
            },
            {
                OptionComponent: NewsletterSubscribeCommonOption,
                props: this.getProps(),
                selector: ".o_newsletter_popup",
                applyTo: ".s_newsletter_list",
            },
            {
                template: "html_builder.MailingListSubscribeFormOption",
                selector: ".s_newsletter_subscribe_form",
            },
        ],
    };

    getProps() {
        return {
            fetchMailingLists: this.dependencies.mailingListSubscribeOption.fetchMailingLists,
            hasRecaptcha: this.dependencies.recaptchaSubscribeOption.hasRecaptcha,
        };
    }
}

registry
    .category("website-plugins")
    .add(NewsletterSubscribeCommonOptionPlugin.id, NewsletterSubscribeCommonOptionPlugin);
