import { BaseOptionComponent } from "@html_builder/core/utils";

export class SpacingOption extends BaseOptionComponent {
    static template = "website.SpacingOption";
    static props = {
        level: { type: Number, optional: true },
        applyTo: { type: String, optional: true },
    };
    static defaultProps = {
        level: 0,
    };
}
