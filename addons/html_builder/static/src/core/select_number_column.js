import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { areColsCustomized } from "@html_builder/utils/column_layout_utils";

export class SelectNumberColumn extends BaseOptionComponent {
    static template = "html_builder.SelectNumberColumn";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const columnEls = editingElement.querySelector(":scope > .row")?.children;
            return {
                isCustomColumn:
                    columnEls &&
                    areColsCustomized(
                        columnEls,
                        this.env.editor.config.isMobileView(editingElement),
                        this.env.editor.config.mobileBreakpoint
                    ),
                canHaveZeroColumns: editingElement.matches(".s_allow_columns"),
            };
        });
    }
}
