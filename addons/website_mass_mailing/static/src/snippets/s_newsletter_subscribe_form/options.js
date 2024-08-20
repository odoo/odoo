import { registerWebsiteOption } from "@website/js/editor/snippets.registry";
import { NewsletterMailingList } from "../s_newsletter_block/options";

registerWebsiteOption("NewsletterSubscribeForm", {
    selector: ".js_subscribe", // TODO: @owl-options change to .s_newsletter_subscribe_form ?
    dropNear: "p, h1, h2, h3, blockquote, .card",
});

registerWebsiteOption("NewsletterSubscribeFormMailingList", {
    Class: NewsletterMailingList,
    template: "website_mass_mailing.newsletter_mailing_list_options",
    selector: ".s_newsletter_subscribe_form",
    exclude: ".s_newsletter_list .s_newsletter_subscribe_form, .o_newsletter_popup .s_newsletter_subscribe_form",
});
