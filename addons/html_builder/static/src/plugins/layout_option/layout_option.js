import { useIsActiveItem } from "@html_builder/core/building_blocks/utils";
import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "../../core/default_builder_components";
import { AddElementOption } from "./add_element_option";
import { SelectNumberColumn } from "./select_number_column";
import { SpacingOption } from "./spacing_option_plugin";

export class LayoutOption extends Component {
    static template = "html_builder.LayoutOption";
    static components = {
        ...defaultBuilderComponents,
        SelectNumberColumn,
        SpacingOption,
        AddElementOption,
    };
    static props = {};

    setup() {
        this.isActiveItem = useIsActiveItem();
    }
}

export class LayoutGridOption extends Component {
    static template = "html_builder.LayoutGridOption";
    static components = {
        ...defaultBuilderComponents,
        SpacingOption,
        AddElementOption,
    };
    static props = {};
}

export class LayoutColumnOption extends Component {
    static template = "html_builder.LayoutColumnOption";
    static components = {
        ...defaultBuilderComponents,
        SelectNumberColumn,
    };
    static props = {};
}
