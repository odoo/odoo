import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class CTABadgeOptionPlugin extends Plugin {
    static id = "ctaBadgeOption";
    resources = {
        builder_options: [
            {
                template: "website.CTABadgeOption",
                selector: ".s_cta_badge",
            },
        ],
        so_content_addition_selector: [".s_cta_badge"],
    };
}
registry.category("website-plugins").add(CTABadgeOptionPlugin.id, CTABadgeOptionPlugin);
