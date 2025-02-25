import { useIsActiveItem } from "@html_builder/core/building_blocks/utils";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Component } from "@odoo/owl";

export class VisibilityOption extends Component {
    static template = "html_builder.VisibilityOption";
    static props = {
        websiteSession: true,
    };
    static components = { ...defaultBuilderComponents };

    setup() {
        this.isActiveItem = useIsActiveItem();
    }
}
