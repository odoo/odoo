import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "../core/default_builder_components";
import { useDomState } from "../core/building_blocks/utils";
import { SpacingOption } from "./spacing_option_plugin";
import { AddElementOption } from "./add_element_option";

// TODO to import in html_builder
import {
    convertToNormalColumn,
    reloadLazyImages,
    toggleGridMode,
} from "@html_builder/utils/grid_layout_utils";
import { Button } from "./button";

export class LayoutOption extends Component {
    static template = "html_builder.LayoutOption";
    static components = { ...defaultBuilderComponents, Button, SpacingOption, AddElementOption };
    static props = {};

    setup() {
        this.state = useDomState(() => ({
            elementLayout: this.isGrid() ? "grid" : "column",
            columnCount: this.getRow()?.children.length,
        }));
    }
    getRow() {
        return this.env.getEditingElement().querySelector(".row");
    }
    isGrid() {
        const rowEl = this.getRow();
        return rowEl && rowEl.classList.contains("o_grid_mode");
    }
    setGridLayout() {
        if (this.isGrid()) {
            // Prevent toggling grid mode twice.
            return;
        }
        toggleGridMode(this.env.getEditingElement().querySelector(".container"));
        this.env.editor.shared.history.addStep();
    }
    setColumnLayout() {
        // Toggle normal mode only if grid mode was activated (as it's in
        // normal mode by default).
        if (!this.isGrid()) {
            return;
        }
        const rowEl = this.getRow();

        // Removing the grid class
        rowEl.classList.remove("o_grid_mode");
        const columnEls = rowEl.children;

        for (const columnEl of columnEls) {
            // Reloading the images.
            reloadLazyImages(columnEl);
            // Removing the grid properties.
            convertToNormalColumn(columnEl);
        }
        // Removing the grid properties.
        delete rowEl.dataset.rowCount;
        // Kept for compatibility.
        rowEl.style.removeProperty("--grid-item-padding-x");
        rowEl.style.removeProperty("--grid-item-padding-y");
        rowEl.style.removeProperty("gap");
        // todo: should use the shared/dependencies/plugins instead when the cleaning PR is merged?
        this.env.editor.shared.history.addStep();
    }
    changeColumnCount(nbColumns) {
        console.warn(`changeColumnCount:`, nbColumns);
    }
}
