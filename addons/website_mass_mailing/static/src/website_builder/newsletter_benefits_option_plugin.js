import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { after, VERTICAL_ALIGNMENT } from "@html_builder/utils/option_sequence";

class NewsletterBenefitsOptionPlugin extends Plugin {
    static id = "newsletterBenefitsOption";
    resources = {
        builder_options: [
            withSequence(after(VERTICAL_ALIGNMENT), {
                template: "website_mass_mailing.NewsletterBenefitsOption",
                selector: ".s_newsletter_benefits .s_text_image",
                applyTo: ".row",
            }),
        ],
    };
}
registry.category("website-plugins").add(NewsletterBenefitsOptionPlugin.id, NewsletterBenefitsOptionPlugin);
