import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class BadgeOptionPlugin extends Plugin {
    static id = "badgeOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        so_content_addition_selectors: [".s_badge"],
        region_properties: { is: ".s_badge", splittable: false },
    };
}
registry.category("builder-plugins").add(BadgeOptionPlugin.id, BadgeOptionPlugin);
