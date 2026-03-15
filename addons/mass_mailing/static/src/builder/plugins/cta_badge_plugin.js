import { CTABadgeOption } from "@html_builder/plugins/cta_badge_option_plugin";
import { BLOCK_ALIGN } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class MassMailingCTABadgeOption extends CTABadgeOption {
    static selector = ".s_cta_badge";
    static template = "mass_mailing.CTABadgeOption";
}

export class CTABadgePlugin extends Plugin {
    static id = "mass_mailing.CTABadgePlugin";
    resources = {
        builder_options: [withSequence(BLOCK_ALIGN, MassMailingCTABadgeOption)],
        so_content_addition_selector: [".s_cta_badge"],
    };
}

registry.category("mass_mailing-plugins").add(CTABadgePlugin.id, CTABadgePlugin);
