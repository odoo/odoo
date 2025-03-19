import { useBuilderComponents, useIsActiveItem } from "@html_builder/core/utils";
import { Component } from "@odoo/owl";

export class VisibilityOption extends Component {
    static template = "html_builder.VisibilityOption";
    static props = {
        websiteSession: true,
    };

    setup() {
        useBuilderComponents();
        this.isActiveItem = useIsActiveItem();
    }
}
