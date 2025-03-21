import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class CTABadgeOptionPlugin extends Plugin {
    static id = "ctaBadgeOption";
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
