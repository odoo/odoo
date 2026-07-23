import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { t, useProps } from "@odoo/owl";

export class MediaSizeOption extends BaseOptionComponent {
    static template = "html_builder.MediaSizeOption";
    props = useProps({
        level: t.number().optional(0),
    });
}
