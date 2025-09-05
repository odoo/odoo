import { LayoutColumnOption } from "@html_builder/plugins/layout_column_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class ReviewsWallOptionPlugin extends Plugin {
    static id = "mass_mailing.ReviewsWallOptionPlugin";
    resources = {
        builder_options: [
            {
                selector: ".s_reviews_wall .s_mail_blockquote",
                template: "mass_mailing.CustomerTestimonialsBlockquote",
            },
            {
                selector: ".s_reviews_wall",
                applyTo: ":scope .container:has(> .row .s_mail_blockquote)",
                OptionComponent: LayoutColumnOption,
            },
        ],
    };
}

registry.category("mass_mailing-plugins").add(ReviewsWallOptionPlugin.id, ReviewsWallOptionPlugin);
