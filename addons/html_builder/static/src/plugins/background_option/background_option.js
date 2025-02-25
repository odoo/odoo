import { useIsActiveItem } from "@html_builder/core/building_blocks/utils";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Component } from "@odoo/owl";
import { BackgroundPositionOption } from "./background_position_option";
import { BackgroundImageOption } from "./background_image_option";
import { BackgroundShapeOption } from "./background_shape_option";

export class BackgroundOption extends Component {
    static template = "html_builder.BackgroundOption";
    static components = {
        ...defaultBuilderComponents,
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
        this.isActiveItem = useIsActiveItem();
    }
}
