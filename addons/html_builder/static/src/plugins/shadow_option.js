import { BaseOptionComponent } from "@html_builder/core/utils";

export class ShadowOption extends BaseOptionComponent {
    static template = "html_builder.ShadowOption";
    static props = {
        setShadowModeAction: { type: String, optional: true },
        setShadowAction: { type: String, optional: true },
    };
    static defaultProps = {
        setShadowModeAction: "setShadowMode",
        setShadowAction: "setShadow",
    };
}
