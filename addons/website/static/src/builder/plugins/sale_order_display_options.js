/** @odoo-module **/

import { BaseOptionComponent } from "@html_builder/core/utils";
import { BuilderSelect } from "@html_builder/core/building_blocks/builder_select";
import { BuilderSelectItem } from "@html_builder/core/building_blocks/builder_select_item";
import { BuilderRow } from "@html_builder/core/building_blocks/builder_row";
import { BuilderCheckbox } from "@html_builder/core/building_blocks/builder_checkbox";

export class SaleOrderDisplayOptions extends BaseOptionComponent {
    static template = "website.SaleOrderDisplayOptions";

    static components = {
        BuilderRow,
        BuilderSelect,
        BuilderSelectItem,
        BuilderCheckbox,
    };

    setup() {
        super.setup();
    }
}
