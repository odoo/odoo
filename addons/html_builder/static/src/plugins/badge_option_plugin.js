import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class BadgeOptionPlugin extends Plugin {
    static id = "badgeOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        so_content_addition_selectors: [".s_badge"],
        is_node_splittable_predicates: (node) => {
            if (node.classList?.contains("s_badge")) {
                return false;
            }
        },
    };
}
registry.category("builder-plugins").add(BadgeOptionPlugin.id, BadgeOptionPlugin);
