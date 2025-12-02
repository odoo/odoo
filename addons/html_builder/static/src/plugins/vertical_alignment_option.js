import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class VerticalAlignmentOption extends BaseOptionComponent {
    static id = "vertical_alignment_option";
    static template = "html_builder.VerticalAlignmentOption";
    static props = {
        level: { type: Number, optional: true },
        justify: { type: Boolean, optional: true },
    };
    static defaultProps = {
        level: 1,
        justify: true,
    };
}

registry.category("builder-options").add(VerticalAlignmentOption.id, VerticalAlignmentOption);
