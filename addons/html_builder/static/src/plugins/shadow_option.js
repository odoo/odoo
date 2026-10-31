import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { _t } from "@web/core/l10n/translation";

export class ShadowOption extends BaseOptionComponent {
    static template = "html_builder.ShadowOption";
    static props = {
        setShadowClassAction: { type: String, optional: true },
        setShadowModeAction: { type: String, optional: true },
        setShadowStyleAction: { type: String, optional: true },
    };
    static defaultProps = {
        setShadowClassAction: "setShadowClass",
        setShadowModeAction: "setShadowMode",
        setShadowStyleAction: "setShadowStyle",
    };

    getEditAction(shadowClass) {
        return {
            title: _t("Edit"),
            onClick: () => this.env.editShadow(shadowClass),
        };
    }
}
