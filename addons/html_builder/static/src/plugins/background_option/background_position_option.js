import { useIsActiveItem } from "@html_builder/core/building_blocks/utils";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Component } from "@odoo/owl";

export class BackgroundPositionOption extends Component {
    static template = "html_builder.BackgroundPositionOption";
    static components = {
        ...defaultBuilderComponents,
    };
    static props = {};
    setup() {
        this.isActiveItem = useIsActiveItem();
    }
}
