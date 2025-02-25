import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Component } from "@odoo/owl";
import { SpacingOption } from "../spacing_option_plugin";
import { AddElementOption } from "../add_element_option";
import { ImageShapeOption } from "./image_shape_option";
import { useIsActiveItem } from "@html_builder/core/building_blocks/utils";

export class ImageToolOption extends Component {
    static template = "html_builder.ImageToolOption";
    static components = {
        ...defaultBuilderComponents,
        SpacingOption,
        AddElementOption,
        ImageShapeOption,
    };
    static props = {};
    setup() {
        this.isActiveItem = useIsActiveItem();
    }
}
