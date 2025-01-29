import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export const card_parent_handlers =
    ".s_three_columns .row > div, .s_comparisons .row > div, .s_cards_grid .row > div, .s_cards_soft .row > div, .s_product_list .row > div";

class CTABadgeOptionPlugin extends Plugin {
    static id = "CTABadgeOption";
    resources = {
        builder_options: [
            {
                template: "html_builder.CTABadgeOption",
                selector: ".s_cta_badge",
            },
        ],
    };
}
registry.category("website-plugins").add(CTABadgeOptionPlugin.id, CTABadgeOptionPlugin);
