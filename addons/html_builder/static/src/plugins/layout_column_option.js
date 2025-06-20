import { SelectNumberColumn } from "@html_builder/core/select_number_column";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class LayoutColumnOption extends BaseOptionComponent {
    static template = "html_builder.LayoutColumnOption";
    static components = {
        SelectNumberColumn,
    };
    static props = {};
}
