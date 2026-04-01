import { getRow } from "@html_builder/utils/column_layout_utils";
import {
    convertToNormalColumn,
    reloadLazyImages,
    toggleGridMode,
} from "@html_builder/utils/grid_layout_utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { LayoutGridOption, LayoutOption } from "./layout_option";
import { withSequence } from "@html_editor/utils/resource";
import { LAYOUT, LAYOUT_GRID } from "@website/builder/option_sequence";
import { BuilderAction } from "@html_builder/core/builder_action";

class LayoutOptionPlugin extends Plugin {
    static id = "LayoutOption";
    static dependencies = ["clone", "selection"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [
            withSequence(LAYOUT, LayoutOption),
            withSequence(LAYOUT_GRID, LayoutGridOption),
        ],
        on_cloned_handlers: this.onCloned.bind(this),
        builder_actions: {
            SetGridLayoutAction,
            SetColumnLayoutAction,
        },
    };
    onCloned({ cloneEl }) {
        const cloneElClassList = cloneEl.classList;
        const offsetClasses = [...cloneElClassList].filter((cls) =>
            cls.match(/^offset-(lg-)?([0-9]{1,2})$/)
        );
        cloneElClassList.remove(...offsetClasses);
    }
}

const isGrid = (el) => {
    const rowEl = getRow(el);
    return !!(rowEl && rowEl.classList.contains("o_grid_mode"));
};
export class SetGridLayoutAction extends BuilderAction {
    static id = "setGridLayout";
    static dependencies = ["selection"];
    apply({ editingElement }) {
        // TODO no preview/apply if it s isApplied
        if (isGrid(editingElement)) {
            return;
        }
        toggleGridMode(
            editingElement,
            this.dependencies.selection.preserveSelection,
            this.config.mobileBreakpoint
        );
    }
    isApplied({ editingElement }) {
        return isGrid(editingElement);
    }
}
export class SetColumnLayoutAction extends BuilderAction {
    static id = "setColumnLayout";
    apply({ editingElement }) {
        const rowEl = getRow(editingElement);
        // TODO no preview/apply if it s isApplied
        if (!isGrid(editingElement)) {
            return;
        }

        // Removing the grid class
        rowEl.classList.remove("o_grid_mode");
        const columnEls = rowEl.children;

        for (const columnEl of columnEls) {
            // Reloading the images.
            reloadLazyImages(columnEl);
            // Removing the grid properties.
            convertToNormalColumn(columnEl, this.config.mobileBreakpoint);
        }
        // Removing the grid properties.
        delete rowEl.dataset.rowCount;
        // Kept for compatibility.
        rowEl.style.removeProperty("--grid-item-padding-x");
        rowEl.style.removeProperty("--grid-item-padding-y");
        rowEl.style.removeProperty("gap");
    }
    isApplied({ editingElement }) {
        return !isGrid(editingElement);
    }
}
registry.category("website-plugins").add(LayoutOptionPlugin.id, LayoutOptionPlugin);
