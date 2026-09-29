import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useProps, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class ShadowOption extends BaseOptionComponent {
    static template = "html_builder.ShadowOption";
    props = useProps({
        setShadowClassAction: t.string().optional("setShadowClass"),
        setShadowModeAction: t.string().optional("setShadowMode"),
        setShadowStyleAction: t.string().optional("setShadowStyle"),
    });

    getEditAction(shadowClass) {
        return {
            title: _t("Edit in Theme Tab"),
            onClick: () => this.env.editThemeOption(shadowClass, "theme-shadow"),
        };
    }
}
