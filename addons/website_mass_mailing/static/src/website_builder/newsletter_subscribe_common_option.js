import { BaseOptionComponent } from "@html_builder/core/utils";
import { MailingListSubscribeOption } from "./mailing_list_subscribe_option";
import { RecaptchaSubscribeOption } from "./recaptcha_subscribe_option";

export class NewsletterSubscribeCommonOptionBase extends BaseOptionComponent {
    static template = "website_mass_mailing.NewsletterSubscribeCommonOption";
    static components = {
        MailingListSubscribeOption,
        RecaptchaSubscribeOption,
    };
}

export class NewsletterSubscribeCommonOption extends NewsletterSubscribeCommonOptionBase {
    static selector = ".s_newsletter_list";
    static exclude = [
        ".s_newsletter_block .s_newsletter_list",
        ".o_newsletter_popup .s_newsletter_list",
        ".s_newsletter_box .s_newsletter_list",
        ".s_newsletter_centered .s_newsletter_list",
        ".s_newsletter_grid .s_newsletter_list",
    ].join(", ");
}

export class NewsletterSubscribeCommonPopupOption extends NewsletterSubscribeCommonOptionBase {
    static selector = ".o_newsletter_popup";
    static applyTo = ".s_newsletter_list";
}
