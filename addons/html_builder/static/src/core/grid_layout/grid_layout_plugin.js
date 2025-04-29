import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import {
    getGridItemProperties,
    getGridProperties,
    resizeGrid,
    setElementToMaxZindex,
} from "@html_builder/utils/grid_layout_utils";
import { isMobileView } from "@html_builder/utils/utils";

const gridItemSelector = ".row.o_grid_mode > div.o_grid_item";

function isGridItem(el) {
    return el.matches(gridItemSelector);
}

export class GridLayoutPlugin extends Plugin {
    static id = "gridLayout";
    static dependencies = ["history"];
    resources = {
        get_overlay_buttons: withSequence(0, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
        on_cloned_handlers: this.onCloned.bind(this),
        on_snippet_preview_handlers: this.adjustGridItem.bind(this),
        on_snippet_dropped_handlers: this.adjustGridItem.bind(this),
    };

    setup() {
        this.overlayTarget = null;
    }

    getActiveOverlayButtons(target) {
        if (!isGridItem(target)) {
            this.overlayTarget = null;
            return [];
        }

        const buttons = [];
        this.overlayTarget = target;
        if (!isMobileView(this.overlayTarget)) {
            buttons.push(
                {
                    class: "o_send_back",
                    title: _t("Send to back"),
                    handler: this.sendGridItemToBack.bind(this),
                },
                {
                    class: "o_bring_front",
                    title: _t("Bring to front"),
                    handler: this.bringGridItemToFront.bind(this),
                }
            );
        }
        return buttons;
    }

    onCloned({ cloneEl }) {
        if (isGridItem(cloneEl)) {
            // If it is a grid item, shift the clone by one cell to the right
            // and to the bottom, wrap to the first column if we reached the
            // last one.
            let { rowStart, rowEnd, columnStart, columnEnd } = getGridItemProperties(cloneEl);
            const columnSpan = columnEnd - columnStart;
            columnStart = columnEnd === 13 ? 1 : columnStart + 1;
            columnEnd = columnStart + columnSpan;
            const newGridArea = `${rowStart + 1} / ${columnStart} / ${rowEnd + 1} / ${columnEnd}`;
            cloneEl.style.gridArea = newGridArea;

            // Update the z-index and the grid row count.
            const rowEl = cloneEl.parentElement;
            setElementToMaxZindex(cloneEl, rowEl);
            resizeGrid(rowEl);
        }
    }

    adjustGridItem({ snippetEl }) {
        const gridItemEl = snippetEl.closest(".o_grid_item");
        if (gridItemEl) {
            // Update the grid item height when previewing and dropping a
            // snippet in it.
            const rowEl = gridItemEl.parentElement;
            const { rowGap, rowSize } = getGridProperties(rowEl);
            const { rowStart, rowEnd } = getGridItemProperties(gridItemEl);
            const oldRowSpan = rowEnd - rowStart;

            // Compute the new height.
            const height = gridItemEl.scrollHeight;
            const rowSpan = Math.ceil((height + rowGap) / (rowSize + rowGap));
            gridItemEl.style.gridRowEnd = rowStart + rowSpan;
            gridItemEl.classList.remove(`g-height-${oldRowSpan}`);
            gridItemEl.classList.add(`g-height-${rowSpan}`);
            resizeGrid(rowEl);
        }
    }

    sendGridItemToBack() {
        const rowEl = this.overlayTarget.parentNode;
        const columnEls = [...rowEl.children].filter((el) => el !== this.overlayTarget);
        const minZindex = Math.min(...columnEls.map((el) => el.style.zIndex));

        // While the minimum z-index is not 0, it is OK to decrease it and to
        // set the column to it. Otherwise, the column is set to 0 and the
        // other columns z-index are increased by one.
        if (minZindex > 0) {
            this.overlayTarget.style.zIndex = minZindex - 1;
        } else {
            columnEls.forEach((columnEl) => columnEl.style.zIndex++);
            this.overlayTarget.style.zIndex = 0;
        }
    }

    bringGridItemToFront() {
        const rowEl = this.overlayTarget.parentNode;
        setElementToMaxZindex(this.overlayTarget, rowEl);
    }
}
