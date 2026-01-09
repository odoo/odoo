import { BaseOptionComponent } from "@html_builder/core/utils";
import { CTABadgeOption } from "@html_builder/plugins/cta_badge_option_plugin";
import { BLOCK_ALIGN } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

export class CTABadgeAlignmentOption extends BaseOptionComponent {
    static selector = ".s_cta_badge";
    static template = "mass_mailing.BlockAlignmentOption";
}

patch(CTABadgeOption.prototype, {
    get excludeShadowOption() {
        return (
            super.excludeShadowOption ||
            this.env.getEditingElement().matches(".o_mail_snippet_general")
        );
    },
});

export class CTABadgePlugin extends Plugin {
    static id = "mass_mailing.CTABadgePlugin";
    resources = {
        builder_options: [withSequence(BLOCK_ALIGN, CTABadgeAlignmentOption)],
    };
}

registry.category("mass_mailing-plugins").add(CTABadgePlugin.id, CTABadgePlugin);
