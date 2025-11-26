import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class GridColumnsOption extends BaseOptionComponent {
    static id = "grid_columns_option";
    static template = "website.GridColumnsOption";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isGridMode: editingElement.parentElement.classList.contains("o_grid_mode"),
        }));
    }
}

registry.category("builder-options").add(GridColumnsOption.id, GridColumnsOption);
