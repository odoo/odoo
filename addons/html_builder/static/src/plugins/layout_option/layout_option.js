import { useBuilderComponents, useIsActiveItem } from "@html_builder/core/utils";
import { Component } from "@odoo/owl";
import { AddElementOption } from "./add_element_option";
import { SelectNumberColumn } from "./select_number_column";
import { SpacingOption } from "./spacing_option_plugin";

export class LayoutOption extends Component {
    static template = "html_builder.LayoutOption";
    static components = {
        SelectNumberColumn,
        SpacingOption,
        AddElementOption,
    };
    static props = {};

    setup() {
        useBuilderComponents();
        this.isActiveItem = useIsActiveItem();
    }
}

export class LayoutGridOption extends Component {
    static template = "html_builder.LayoutGridOption";
    static components = {
        SpacingOption,
        AddElementOption,
    };
    static props = {};
    setup() {
        useBuilderComponents();
    }
}

export class LayoutColumnOption extends Component {
    static template = "html_builder.LayoutColumnOption";
    static components = {
        SelectNumberColumn,
    };
    static props = {};
    setup() {
        useBuilderComponents();
    }
}
