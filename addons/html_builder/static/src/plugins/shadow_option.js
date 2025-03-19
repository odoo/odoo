import { Component } from "@odoo/owl";
import { useBuilderComponents, useIsActiveItem } from "@html_builder/core/utils";

export class ShadowOption extends Component {
    static template = "html_builder.ShadowOption";
    static props = {};
    setup() {
        useBuilderComponents();
        this.isActiveItem = useIsActiveItem();
    }
}
