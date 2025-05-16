import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class NewsletterPopupPlugin extends Plugin {
    static id = "newsletterPopup";
    resources = {
        so_snippet_addition_selector: [".o_newsletter_popup"],
    };
}

registry.category("website-plugins").add(NewsletterPopupPlugin.id, NewsletterPopupPlugin);
