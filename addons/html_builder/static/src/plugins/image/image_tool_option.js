import { useIsActiveItem } from "@html_builder/core/building_blocks/utils";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Component } from "@odoo/owl";
import { ImageShapeOption } from "./image_shape_option";

export class ImageToolOption extends Component {
    static template = "html_builder.ImageToolOption";
    static components = {
        ...defaultBuilderComponents,
        ImageShapeOption,
    };
    static props = {};
    setup() {
        this.isActiveItem = useIsActiveItem();
    }
}
