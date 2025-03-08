import { useDomState, useIsActiveItem } from "@html_builder/core/building_blocks/utils";
import { areColsCustomized } from "@html_builder/utils/column_layout_utils";
import { isMobileView } from "@html_builder/utils/utils";
import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "../../core/default_builder_components";

export class SelectNumberColumn extends Component {
    static template = "html_builder.SelectNumberColumn";
    static components = { ...defaultBuilderComponents };
    static props = {};

    setup() {
        this.isActiveItem = useIsActiveItem();
        this.state = useDomState((editingElement) => {
            const columnEls = editingElement?.querySelector(":scope > .row")?.children;
            return {
                isCustomColumn:
                    columnEls && areColsCustomized(columnEls, isMobileView(editingElement)),
            };
        });
    }
}
