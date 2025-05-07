import { BaseOptionComponent } from "@html_builder/core/utils";

export class VerticalAlignmentOption extends BaseOptionComponent {
    static template = "website.VerticalAlignmentOption";
    static props = {
        level: { type: Number, optional: true },
        applyTo: { type: String, optional: true },
        justify: { type: Boolean, optional: true },
    };
    static defaultProps = {
        level: 0,
        justify: true,
    };
}
