import { getFirstItem, getNbColumns } from "@html_builder/utils/column_layout_utils";
import {
    convertToNormalColumn,
    reloadLazyImages,
    toggleGridMode,
    layoutOptionSelector,
} from "@html_builder/utils/grid_layout_utils";
import { isMobileView } from "@html_builder/utils/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { LayoutColumnOption, LayoutGridOption, LayoutOption } from "./layout_option";
import { withSequence } from "@html_editor/utils/resource";
import { LAYOUT, LAYOUT_COLUMN, LAYOUT_GRID } from "@website/builder/option_sequence";
import { BuilderAction } from "@html_builder/core/builder_action";

class LayoutOptionPlugin extends Plugin {
    static id = "LayoutOption";
    static dependencies = ["clone", "selection"];
    resources = {
        builder_options: [
            withSequence(LAYOUT, {
                OptionComponent: LayoutOption,
                ...layoutOptionSelector,
            }),
            withSequence(LAYOUT_COLUMN, {
                OptionComponent: LayoutColumnOption,
                selector: "section.s_features_grid, section.s_process_steps",
                applyTo: ":scope > *:has(> .row), :scope > .s_allow_columns",
            }),
            withSequence(LAYOUT_GRID, {
                OptionComponent: LayoutGridOption,
                selector:
                    "section.s_masonry_block, section.s_quadrant, section.s_image_frame, section.s_card_offset, section.s_contact_info, section.s_framed_intro",
                applyTo: ":scope > *:has(> .row)",
            }),
        ],
        on_cloned_handlers: this.onCloned.bind(this),
        builder_actions: {
            SetGridLayoutAction,
            SetColumnLayoutAction,
            ChangeColumnCountAction,
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

const getRow = (el) => el.querySelector(":scope > .row");
const isGrid = (el) => {
    const rowEl = getRow(el);
    return !!(rowEl && rowEl.classList.contains("o_grid_mode"));
};
class SetGridLayoutAction extends BuilderAction {
    static id = "setGridLayout";
    static dependencies = ["selection"];
    apply({ editingElement }) {
        // TODO no preview/apply if it s isApplied
        if (isGrid(editingElement)) {
            return;
        }
        toggleGridMode(editingElement, this.dependencies.selection.preserveSelection);
    }
    isApplied({ editingElement }) {
        return isGrid(editingElement);
    }
}
class SetColumnLayoutAction extends BuilderAction {
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
            convertToNormalColumn(columnEl);
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
class ChangeColumnCountAction extends BuilderAction {
    static id = "changeColumnCount";
    static dependencies = ["selection", "clone"];
    apply({ editingElement, value: nbColumns }) {
        if (nbColumns === "custom") {
            return;
        }

        let rowEl = getRow(editingElement);
        let columnEls, prevNbColumns;
        if (!rowEl) {
            // If there is no row, create one and wrap the content
            // in a column.
            const cursors = this.dependencies.selection.preserveSelection();
            rowEl = document.createElement("div");
            const columnEl = document.createElement("div");
            rowEl.classList.add("row");
            columnEl.classList.add("col-lg-12");
            columnEl.append(...editingElement.children);
            rowEl.append(columnEl);
            editingElement.append(rowEl);
            cursors.restore();

            columnEls = [columnEl];
            prevNbColumns = 0;
        } else {
            columnEls = rowEl.children;
            prevNbColumns = getNbColumns(columnEls, isMobileView(this.editable));
        }

        if (nbColumns === prevNbColumns) {
            return;
        }
        this._resizeColumns(columnEls, nbColumns || 1);

        const itemsDelta = nbColumns - rowEl.children.length;
        if (itemsDelta > 0) {
            for (let i = 0; i < itemsDelta; i++) {
                const lastEl = rowEl.lastElementChild;
                this.dependencies.clone.cloneElement(lastEl);
            }
        }

        // If "None" columns was chosen, unwrap the content from
        // the column and the row and remove them.
        if (nbColumns === 0) {
            const cursors = this.dependencies.selection.preserveSelection();
            const columnEl = editingElement.querySelector(".row > div");
            editingElement.append(...columnEl.children);
            rowEl.remove();
            cursors.restore();
        }
    }
    isApplied({ editingElement, value }) {
        const columnEls = getRow(editingElement)?.children;
        return getNbColumns(columnEls, isMobileView(this.editable)) === value;
    }
    /**
     * Resizes the columns for the mobile or desktop view.
     *
     * @private
     * @param {HTMLCollection} columnEls - the elements to resize
     * @param {integer} nbColumns - the number of wanted columns
     */
    _resizeColumns(columnEls, nbColumns) {
        const isMobile = isMobileView(this.editable);
        const itemSize = Math.floor(12 / nbColumns) || 1;
        const firstItem = getFirstItem(columnEls, isMobile);
        const firstItemOffset = Math.floor((12 - itemSize * nbColumns) / 2);

        const resolutionModifier = isMobile ? "" : "-lg";
        const replacingRegex =
            // (?!\S): following char cannot be a non-space character
            new RegExp(`(?:^|\\s+)(col|offset)${resolutionModifier}(-\\d{1,2})?(?!\\S)`, "g");

        for (const columnEl of columnEls) {
            columnEl.className = columnEl.className.replace(replacingRegex, "");
            columnEl.classList.add(`col${resolutionModifier}-${itemSize}`);
            if (firstItemOffset && columnEl === firstItem) {
                columnEl.classList.add(`offset${resolutionModifier}-${firstItemOffset}`);
            }
            const hasMobileOffset = columnEl.className.match(/(^|\s+)offset-\d{1,2}(?!\S)/);
            const hasDesktopOffset = columnEl.className.match(/(^|\s+)offset-lg-[1-9][0-1]?(?!\S)/);
            columnEl.classList.toggle("offset-lg-0", hasMobileOffset && !hasDesktopOffset);
        }
    }
}
registry.category("website-plugins").add(LayoutOptionPlugin.id, LayoutOptionPlugin);
