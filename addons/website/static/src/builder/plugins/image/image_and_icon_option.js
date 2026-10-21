import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";
import { useProps, t } from "@odoo/owl";

export class ImageAndIconOption extends BaseOptionComponent {
    static id = "image_and_icon_option";
    static template = "website.ImageAndIconOption";
    props = useProps({
        // False for images as wide as their container, where an alignment has
        // no effect.
        withAlignment: t.boolean().optional(true),
    });
}

registry.category("website-options").add(ImageAndIconOption.id, ImageAndIconOption);
