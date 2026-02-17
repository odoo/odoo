import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CTABadgeOptionPlugin extends Plugin {
    static id = "ctaBadgeOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        so_content_addition_selector: [".s_cta_badge"],
    };
}
registry.category("builder-plugins").add(CTABadgeOptionPlugin.id, CTABadgeOptionPlugin);
