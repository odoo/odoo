import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { ShadowOption } from "@html_builder/plugins/shadow_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CTABadgeOption extends BaseOptionComponent {
    static template = "html_builder.CTABadgeOption";
    static selector = ".s_cta_badge";
    static components = { BorderConfigurator, ShadowOption };
}

class CTABadgeOptionPlugin extends Plugin {
    static id = "ctaBadgeOption";
    resources = {
        builder_options: [CTABadgeOption],
        so_content_addition_selector: [".s_cta_badge"],
    };
}
registry.category("builder-plugins").add(CTABadgeOptionPlugin.id, CTABadgeOptionPlugin);
