import { before, SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";
import { POPUP } from "@website/builder/plugins/options/popup_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { NewsletterSubscribeCommonOption, NewsletterSubscribeCommonPopupOption } from "./newsletter_subscribe_common_option";
import { BaseOptionComponent } from "@html_builder/core/utils";

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
    };
}

registry
    .category("website-plugins")
    .add(NewsletterSubscribeCommonOptionPlugin.id, NewsletterSubscribeCommonOptionPlugin);
