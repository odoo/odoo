import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { LayoutColumnOption } from "@html_builder/plugins/layout_column_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CustomerTestimonialsBlockquote extends BaseOptionComponent {
    static template = "mass_mailing.CustomerTestimonialsBlockquote";
    static selector = ".s_reviews_wall .s_mail_blockquote";
    static components = { BorderConfigurator };
}

export class MassMailingLayoutColumnOption extends LayoutColumnOption {
    static selector = ".s_reviews_wall .container";
    static applyTo = ":scope > .row:has(> .s_mail_blockquote), :scope > .row > .s_allow_columns";
}

class ReviewsWallOptionPlugin extends Plugin {
    static id = "mass_mailing.ReviewsWallOptionPlugin";
    resources = {
        builder_options: [CustomerTestimonialsBlockquote, MassMailingLayoutColumnOption],
    };
}

registry.category("mass_mailing-plugins").add(ReviewsWallOptionPlugin.id, ReviewsWallOptionPlugin);
