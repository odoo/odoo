import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Component } from "@odoo/owl";
import { ShapeSelector } from "../shape/shape_selector";
import { imageShapeDefinitions } from "./image_shapes_definition";

export class ImageShapeOption extends Component {
    static template = "html_builder.ImageShapeOption";
    static components = { ...defaultBuilderComponents };
    static props = {};
    setup() {
        this.customizeTabPlugin = this.env.editor.shared.customizeTab;
    }
    showImageShapes() {
        this.customizeTabPlugin.openCustomizeComponent(
            ShapeSelector,
            this.env.getEditingElements(),
            {
                shapeActionId: "setImageShape",
                shapeGroups: this.getImageShapeGroups(),
            }
        );
    }
    getImageShapeGroups() {
        return imageShapeDefinitions;
    }
}
