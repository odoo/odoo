import { useBuilderComponents, useIsActiveItem } from "@html_builder/core/utils";
import { Component } from "@odoo/owl";
import { ImageShapeOption } from "./image_shape_option";

export class ImageToolOption extends Component {
    static template = "html_builder.ImageToolOption";
    static components = {
        ImageShapeOption,
    };
    static props = {};
    setup() {
        useBuilderComponents();
        this.isActiveItem = useIsActiveItem();
    }
}
