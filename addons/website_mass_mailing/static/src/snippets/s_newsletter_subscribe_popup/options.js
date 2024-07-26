import { registerSnippetAdditionSelector } from "@web_editor/js/editor/snippets.registry";
import { registerWebsiteOption } from "@website/js/editor/snippets.registry";
import { NewsletterMailingList } from "../s_newsletter_block/options";

registerWebsiteOption("NewsletterSubscribePopup", {
    Class: NewsletterMailingList,
    template: "website_mass_mailing.newsletter_mailing_list_options",
    selector: ".o_newsletter_popup",
    target: ".s_newsletter_list",
});
registerSnippetAdditionSelector(".o_newsletter_popup");
