import { SelectNumberColumn } from "@html_builder/core/select_number_column";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class LayoutColumnOption extends BaseOptionComponent {
    static template = "html_builder.LayoutColumnOption";
    static components = {
        SelectNumberColumn,
    };
    static selector = "section.s_features_grid, section.s_process_steps";
    static applyTo = ":scope > *:has(> .row), :scope > .s_allow_columns";
    static name = "layoutColumnOption";
}
