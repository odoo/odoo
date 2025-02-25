import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "../core/default_builder_components";
import { useIsActiveItem } from "@html_builder/core/building_blocks/utils";

export class ShadowOption extends Component {
    static template = "html_builder.ShadowOption";
    static components = { ...defaultBuilderComponents };
    static props = {};
    setup() {
        this.isActiveItem = useIsActiveItem();
    }
}
