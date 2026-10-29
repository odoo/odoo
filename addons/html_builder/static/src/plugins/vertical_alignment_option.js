import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useProps, t } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class VerticalAlignmentOption extends BaseOptionComponent {
    static id = "vertical_alignment_option";
    static template = "html_builder.VerticalAlignmentOption";
    props = useProps({
        level: t.boolean().optional(true),
        justify: t.boolean().optional(true),
    });
}

registry.category("builder-options").add(VerticalAlignmentOption.id, VerticalAlignmentOption);
