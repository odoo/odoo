import { useBuilderComponents, useIsActiveItem } from "@html_builder/core/utils";
import { Component } from "@odoo/owl";
import { BackgroundPositionOption } from "./background_position_option";
import { BackgroundImageOption } from "./background_image_option";
import { BackgroundShapeOption } from "./background_shape_option";

export class BackgroundOption extends Component {
    static template = "html_builder.BackgroundOption";
    static components = {
        BackgroundImageOption,
        BackgroundPositionOption,
        BackgroundShapeOption,
    };
    static props = {
        withColors: { type: Boolean },
        withImages: { type: Boolean },
        withColorCombinations: { type: Boolean },
        withGradient: { type: Boolean },
        withShapes: { type: Boolean, optional: true },
    };
    static defaultProps = {
        withShapes: false,
    };
    setup() {
        useBuilderComponents();
        this.isActiveItem = useIsActiveItem();
    }
    showColorFilter() {
        return this.isActiveItem("toggle_bg_image_id");
    }
}
