import { Component } from "@odoo/owl";
import { useBuilderComponents, useDomState } from "../../core/utils";

export class GridColumnsOption extends Component {
    static template = "html_builder.GridColumnsOption";
    static props = {};

    setup() {
        useBuilderComponents();
        this.state = useDomState((editingElement) => ({
            isGridMode:
                editingElement && editingElement.parentElement.classList.contains("o_grid_mode"),
        }));
    }
}
