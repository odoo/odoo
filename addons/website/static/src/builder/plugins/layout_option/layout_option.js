import { BaseOptionComponent } from "@html_builder/core/utils";
import { AddElementOption } from "./add_element_option";
import { SelectNumberColumn } from "./select_number_column";
import { SpacingOption } from "./spacing_option";

export class LayoutOption extends BaseOptionComponent {
    static template = "website.LayoutOption";
    static components = {
        SelectNumberColumn,
        SpacingOption,
        AddElementOption,
    };
    static props = {};
}

export class LayoutGridOption extends BaseOptionComponent {
    static template = "website.LayoutGridOption";
    static components = {
        SpacingOption,
        AddElementOption,
    };
    static props = {};
}

export class LayoutColumnOption extends BaseOptionComponent {
    static template = "website.LayoutColumnOption";
    static components = {
        SelectNumberColumn,
    };
    static props = {};
}
