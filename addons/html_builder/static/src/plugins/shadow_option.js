import { BaseOptionComponent } from "@html_builder/core/utils";

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

    getOnClick(shadowClass) {
        return () => this.env.editShadow(shadowClass);
    }
}
