import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

export class NewsletterLayoutOptionPlugin extends Plugin {
    static id = "newsletterLayoutOptionPlugin";
    resources = {
        builder_options: [
            withSequence(1, {
                template: "website_mass_mailing.NewsletterLayoutOption",
                selector: ".s_newsletter_block",
                applyTo:
                    ":scope > .container, :scope > .container-fluid, :scope > .o_container_small",
            }),
        ],
    };
}

registry
    .category("website-plugins")
    .add(NewsletterLayoutOptionPlugin.id, NewsletterLayoutOptionPlugin);
