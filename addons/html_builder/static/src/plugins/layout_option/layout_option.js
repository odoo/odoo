import { useDomState, useIsActiveItem } from "@html_builder/core/building_blocks/utils";
import { areColsCustomized } from "@html_builder/utils/column_layout_utils";
import { isMobileView } from "@html_builder/utils/utils";
import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "../../core/default_builder_components";
import { AddElementOption } from "./add_element_option";
import { SpacingOption } from "./spacing_option_plugin";

export class LayoutOption extends Component {
    static template = "html_builder.LayoutOption";
    static components = { ...defaultBuilderComponents, SpacingOption, AddElementOption };
    static props = {};

    setup() {
        this.isActiveItem = useIsActiveItem();
        this.state = useDomState((editingElement) => {
            const columnEls = editingElement.querySelector(":scope > .container > .row")?.children;
            return {
                isCustomColumn:
                    columnEls && areColsCustomized(columnEls, isMobileView(editingElement)),
            };
        });
    }
}
