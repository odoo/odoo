import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class GridColumnsOption extends BaseOptionComponent {
    static template = "website.GridColumnsOption";
    static selector = ".row:not(.s_col_no_resize) > div";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isGridMode: editingElement.parentElement.classList.contains("o_grid_mode"),
        }));
    }
}
