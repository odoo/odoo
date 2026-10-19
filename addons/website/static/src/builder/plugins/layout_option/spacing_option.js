import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useProps, t } from "@odoo/owl";

export class SpacingOption extends BaseOptionComponent {
    static template = "website.SpacingOption";
    props = useProps({
        level: t.number().optional(0),
        applyTo: t.string().optional(),
    });
}
