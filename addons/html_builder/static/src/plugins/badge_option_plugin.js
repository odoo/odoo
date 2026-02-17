import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class BadgeOptionPlugin extends Plugin {
    static id = "badgeOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        so_content_addition_selector: [".s_badge"],
    };
}
registry.category("builder-plugins").add(BadgeOptionPlugin.id, BadgeOptionPlugin);
