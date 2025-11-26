import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { ShadowOption } from "@html_builder/plugins/shadow_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CTABadgeOption extends BaseOptionComponent {
    static id = "cta_badge_option";
    static template = "html_builder.CTABadgeOption";
    static components = { BorderConfigurator, ShadowOption };
}
registry.category("builder-options").add(CTABadgeOption.id, CTABadgeOption);

export class CTABadgeOptionPlugin extends Plugin {
    static id = "ctaBadgeOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        so_content_addition_selector: [".s_cta_badge"],
    };
}
registry.category("builder-plugins").add(CTABadgeOptionPlugin.id, CTABadgeOptionPlugin);
