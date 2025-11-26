import { SelectNumberColumn } from "@html_builder/core/select_number_column";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { AddElementOption } from "./add_element_option";
import { SpacingOption } from "./spacing_option";

export class LayoutOption extends BaseOptionComponent {
    static id = "layout_option";
    static template = "website.LayoutOption";
    static components = {
        SelectNumberColumn,
        SpacingOption,
        AddElementOption,
    };
}

export class LayoutGridOption extends BaseOptionComponent {
    static id = "layout_grid_option";
    static template = "website.LayoutGridOption";
    static components = {
        SpacingOption,
        AddElementOption,
    };
}

registry.category("builder-options").add(LayoutOption.id, LayoutOption);
registry.category("builder-options").add(LayoutGridOption.id, LayoutGridOption);
