import { SelectNumberColumn } from "@html_builder/core/select_number_column";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class LayoutColumnOption extends BaseOptionComponent {
    static id = "layout_column_option";
    static template = "html_builder.LayoutColumnOption";
    static components = {
        SelectNumberColumn,
    };
}

registry.category("builder-options").add(LayoutColumnOption.id, LayoutColumnOption);
