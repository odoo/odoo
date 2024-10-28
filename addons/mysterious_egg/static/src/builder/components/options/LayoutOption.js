import { Component, useState } from "@odoo/owl";
import { defaultOptionComponents } from "../defaultComponents";
import {
    _convertToNormalColumn,
    _reloadLazyImages,
    _toggleGridMode,
} from "@web_editor/js/common/grid_layout_utils";
import { AddElementOption } from "./AddElementOption";
import { HorizontalAlignmentOption } from "./HorizontalAlignmentOption";
import { SpacingOption } from "./SpacingOption";

export class LayoutOption extends Component {
    static template = "mysterious_egg.LayoutOption";
    static components = {
        ...defaultOptionComponents,
        AddElementOption,
        SpacingOption,
        HorizontalAlignmentOption,
    };
    static props = {
        toolboxElement: Object,
    };
    setup() {
        this.state = useState(this.setState({}));
        this.env.editorBus.addEventListener("STEP_ADDED", () => {
            this.setState(this.state);
        });
        this.layoutButtonsProps = {
            buttons: [
                { id: "grid", label: "Grid" },
                { id: "column", label: "Column" },
            ],
            activeState: this.state,
            isActive: (buttonId, activeState) => buttonId === activeState.elementLayout,
        };
    }
    setState(object) {
        Object.assign(object, {
            elementLayout: this.isGrid() ? "grid" : "column",
            columnCount: this.getRow()?.children.length,
        });
        console.warn(`elementLayout:`, object.elementLayout);

        return object;
    }
    getRow() {
        return this.props.toolboxElement.querySelector(".row");
    }
    isGrid() {
        const rowEl = this.getRow();
        return rowEl && rowEl.classList.contains("o_grid_mode");
    }
    setGridLayout() {
        const rowEl = this.props.toolboxElement.querySelector(".row");
        if (rowEl && rowEl.classList.contains("o_grid_mode")) {
            // Prevent toggling grid mode twice.
            return;
        }
        _toggleGridMode(this.props.toolboxElement.querySelector(".container"));
        this.env.editor.dispatch("ADD_STEP");
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
            _reloadLazyImages(columnEl);
            // Removing the grid properties.
            _convertToNormalColumn(columnEl);
        }
        // Removing the grid properties.
        delete rowEl.dataset.rowCount;
        // Kept for compatibility.
        rowEl.style.removeProperty("--grid-item-padding-x");
        rowEl.style.removeProperty("--grid-item-padding-y");
        rowEl.style.removeProperty("gap");
        // todo: should use the shared/dependencies/plugins instead when the cleaning PR is merged?
        this.env.editor.dispatch("ADD_STEP");
    }
    changeColumnCount(nbColumns) {
        console.warn(`changeColumnCount:`, nbColumns);
    }
}
