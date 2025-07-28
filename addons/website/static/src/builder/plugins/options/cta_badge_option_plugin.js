import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CTABadgeOption extends BaseOptionComponent {
    static template = "website.CTABadgeOption";
    static selector = ".s_cta_badge";
}

class CTABadgeOptionPlugin extends Plugin {
    static id = "ctaBadgeOption";
    resources = {
        builder_options: [CTABadgeOption],
        so_content_addition_selector: [".s_cta_badge"],
    };
}
registry.category("website-plugins").add(CTABadgeOptionPlugin.id, CTABadgeOptionPlugin);
