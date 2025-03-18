import { Component } from "@odoo/owl";
import { useDomState } from "../../core/building_blocks/utils";
import { defaultBuilderComponents } from "../../core/default_builder_components";

export class GridColumnsOption extends Component {
    static template = "html_builder.GridColumnsOption";
    static components = { ...defaultBuilderComponents };
    static props = {};

    setup() {
        this.state = useDomState((editingElement) => ({
            isGridMode:
                editingElement && editingElement.parentElement.classList.contains("o_grid_mode"),
        }));
    }
}
