import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { areColsCustomized } from "@html_builder/utils/column_layout_utils";
import { isMobileView } from "@html_builder/utils/utils";

export class SelectNumberColumn extends BaseOptionComponent {
    static template = "html_builder.SelectNumberColumn";
    static props = {};

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const columnEls = editingElement.querySelector(":scope > .row")?.children;
            return {
                isCustomColumn:
                    columnEls && areColsCustomized(columnEls, isMobileView(editingElement)),
                canHaveZeroColumns: editingElement.matches(".s_allow_columns"),
            };
        });
    }
}
