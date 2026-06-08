import { SelectNumberColumn } from "@html_builder/core/select_number_column";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";
import { SpacingOption } from "./spacing_option";

export class LayoutOption extends BaseOptionComponent {
    static id = "layout_option";
    static template = "website.LayoutOption";
    static components = {
        SelectNumberColumn,
        SpacingOption,
    };
}

export class LayoutGridOption extends BaseOptionComponent {
    static id = "layout_grid_option";
    static template = "website.LayoutGridOption";
    static components = {
        SpacingOption,
    };
}

registry.category("website-options").add(LayoutOption.id, LayoutOption);
registry.category("website-options").add(LayoutGridOption.id, LayoutGridOption);
