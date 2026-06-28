import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { props, t } from "@odoo/owl";

export class MediaSizeOption extends BaseOptionComponent {
    static template = "html_builder.MediaSizeOption";
    props = props({
        level: t.number().optional(0),
    });
}
