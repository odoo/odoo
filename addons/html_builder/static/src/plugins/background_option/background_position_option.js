import { useBuilderComponents, useIsActiveItem } from "@html_builder/core/utils";
import { Component } from "@odoo/owl";

export class BackgroundPositionOption extends Component {
    static template = "html_builder.BackgroundPositionOption";
    static props = {};
    setup() {
        useBuilderComponents();
        this.isActiveItem = useIsActiveItem();
    }
}
