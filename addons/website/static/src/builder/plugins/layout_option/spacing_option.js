import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { props, t } from "@odoo/owl";

export class SpacingOption extends BaseOptionComponent {
    static template = "website.SpacingOption";
    props = props({
        applyTo: t.string().optional(),
    });
}
