import { BaseOptionComponent, useDomState } from "../../core/utils";

export class GridColumnsOption extends BaseOptionComponent {
    static template = "html_builder.GridColumnsOption";
    static props = {};

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isGridMode:
                editingElement && editingElement.parentElement.classList.contains("o_grid_mode"),
        }));
    }
}
