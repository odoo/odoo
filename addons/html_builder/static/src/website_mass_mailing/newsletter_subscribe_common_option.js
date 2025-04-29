import { BaseOptionComponent } from "@html_builder/core/utils";
import { MailingListSubscribeOption } from "./mailing_list_subscribe_option";
import { RecaptchaSubscribeOption } from "./recaptcha_subscribe_option";

export class NewsletterSubscribeCommonOption extends BaseOptionComponent {
    static template = "html_builder.NewsletterSubscribeCommonOption";
    static components = {
        MailingListSubscribeOption,
        RecaptchaSubscribeOption,
    };
    static props = {
        fetchMailingLists: Function,
        hasRecaptcha: Function,
    };
}
