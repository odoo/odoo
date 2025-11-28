import { BaseOptionComponent } from "@html_builder/core/utils";
import { MailingListSubscribeOption } from "./mailing_list_subscribe_option";
import { RecaptchaSubscribeOption } from "./recaptcha_subscribe_option";
import { registry } from "@web/core/registry";

export class NewsletterSubscribeCommonOption extends BaseOptionComponent {
    static id = "newsletter_subscribe_common_option"

    static template = "website_mass_mailing.NewsletterSubscribeCommonOption";
    static components = {
        MailingListSubscribeOption,
        RecaptchaSubscribeOption,
    };
}

registry
    .category("builder-options")
    .add(NewsletterSubscribeCommonOption.id, NewsletterSubscribeCommonOption);
