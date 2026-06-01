import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";

export class VerticalAlignmentOption extends BaseOptionComponent {
    static id = "vertical_alignment_option";
    static template = "html_builder.VerticalAlignmentOption";
    static props = {
        level: { type: Boolean, optional: true },
        justify: { type: Boolean, optional: true },
    };
    static defaultProps = {
        level: true,
        justify: true,
    };
}

registry.category("builder-options").add(VerticalAlignmentOption.id, VerticalAlignmentOption);
