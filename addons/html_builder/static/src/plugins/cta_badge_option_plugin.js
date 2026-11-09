import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CTABadgeOptionPlugin extends Plugin {
    static id = "ctaBadgeOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        so_content_addition_selectors: [".s_cta_badge"],
        is_node_splittable_predicates: (node) => {
            if (node.classList?.contains("s_cta_badge")) {
                return false;
            }
        },
    };
}
registry.category("builder-plugins").add(CTABadgeOptionPlugin.id, CTABadgeOptionPlugin);
