import { BuilderAction } from "@html_builder/core/builder_action";
import { getFirstItem, getNbColumns, getRow } from "@html_builder/utils/column_layout_utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { LayoutColumnOption } from "@html_builder/plugins/layout_column_option";
import { LAYOUT_COLUMN } from "@html_builder/utils/option_sequence";

class LayoutColumnOptionPlugin extends Plugin {
    static id = "LayoutColumnOption";
    static dependencies = ["clone", "selection"];
    resources = {
        builder_options: [withSequence(LAYOUT_COLUMN, LayoutColumnOption)],
        on_cloned_handlers: this.onCloned.bind(this),
        builder_actions: {
            ChangeColumnCountAction,
        },
        selection_placeholder_container_predicates: (container) => {
            if (container.nodeName === "DIV" && container.parentElement.classList.contains("row")) {
                return true;
            }
        },
        selection_blocker_predicates: (blocker) => {
            if (blocker.classList.contains("row")) {
                return false;
            }
        },
    };
    onCloned({ cloneEl }) {
        const cloneElClassList = cloneEl.classList;
        const offsetRegex = new RegExp(`^offset-(${this.config.mobileBreakpoint}-)?([0-9]{1,2})$`);
        const offsetClasses = [...cloneElClassList].filter((cls) => cls.match(offsetRegex));
        cloneElClassList.remove(...offsetClasses);
    }
}

export class ChangeColumnCountAction extends BuilderAction {
    static id = "changeColumnCount";
    static dependencies = ["selection", "clone", "builderOptions"];
    async apply({ editingElement, value: nbColumns }) {
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
            columnEl.classList.add(`col-${this.config.mobileBreakpoint}-12`);
            columnEl.append(...editingElement.children);
            rowEl.append(columnEl);
            editingElement.append(rowEl);
            cursors.restore();

            columnEls = [columnEl];
            prevNbColumns = 0;
        } else {
            columnEls = rowEl.children;
            prevNbColumns = getNbColumns(
                columnEls,
                this.config.isMobileView(this.editable),
                this.config.mobileBreakpoint
            );
        }

        if (nbColumns === prevNbColumns) {
            return;
        }
        this._resizeColumns(columnEls, nbColumns || 1);

        const itemsDelta = nbColumns - rowEl.children.length;
        if (itemsDelta > 0) {
            for (let i = 0; i < itemsDelta; i++) {
                const lastEl = rowEl.lastElementChild;
                await this.dependencies.clone.cloneElement(lastEl, { activateClone: false });
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
        } else if (prevNbColumns === 0) {
            // Activate the first column options.
            const firstColumnEl = editingElement.querySelector(".row > div");
            this.dependencies.builderOptions.setNextTarget(firstColumnEl);
        }
    }
    isApplied({ editingElement, value }) {
        const columnEls = getRow(editingElement)?.children;
        return (
            getNbColumns(
                columnEls,
                this.config.isMobileView(this.editable),
                this.config.mobileBreakpoint
            ) === value
        );
    }
    /**
     * Resizes the columns for the mobile or desktop view.
     *
     * @private
     * @param {HTMLCollection} columnEls - the elements to resize
     * @param {integer} nbColumns - the number of wanted columns
     */
    _resizeColumns(columnEls, nbColumns) {
        const isMobile = this.config.isMobileView(this.editable);
        const itemSize = Math.floor(12 / nbColumns) || 1;
        const firstItem = getFirstItem(columnEls, isMobile);
        const firstItemOffset = Math.floor((12 - itemSize * nbColumns) / 2);

        const resolutionModifier = isMobile ? "" : `-${this.config.mobileBreakpoint}`;
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
            const desktopOffsetRegexp = new RegExp(
                `(^|\\s+)offset-${this.config.mobileBreakpoint}-[1-9][0-1]?(?!\\S)`
            );
            const hasDesktopOffset = columnEl.className.match(desktopOffsetRegexp);
            columnEl.classList.toggle(
                `offset-${this.config.mobileBreakpoint}-0`,
                hasMobileOffset && !hasDesktopOffset
            );
        }
    }
}

registry.category("builder-plugins").add(LayoutColumnOptionPlugin.id, LayoutColumnOptionPlugin);
