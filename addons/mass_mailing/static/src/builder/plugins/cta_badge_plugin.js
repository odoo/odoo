import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CTABadgePlugin extends Plugin {
    static id = "mass_mailing.CTABadgePlugin";
    resources = {
        so_content_addition_selector: [".s_cta_badge"],
    };
}

registry.category("mass_mailing-plugins").add(CTABadgePlugin.id, CTABadgePlugin);
