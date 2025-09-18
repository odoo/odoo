// @ts-check

/** @module @web/views/list/list_virtualization - Row virtualization hook rendering only visible rows plus buffer for large list views */

/**
 * Row virtualization hook for the list view.
 *
 * Wraps `useVirtualGrid` and `ListGridState` to render only visible rows + buffer.
 * Activates automatically when flat row count exceeds threshold and drag-and-drop
 * is not active.  Below threshold, zero overhead — all rows render normally.
 *
 * Usage in ListRenderer.setup():
 *
 *     this.virt = useListVirtualization({
 *         rootRef: this.rootRef,
 *         getGridState: () => this.gridState,
 *         getNbCols: () => this.nbCols,
 *         canResequence: () => this.canResequenceRows,
 *         getEditedRecord: () => this.editedRecord,
 *     });
 *
 *     // In onWillRender, after gridState.rebuild():
 *     this.virt.refresh();
 */

import { onMounted, onPatched } from "@odoo/owl";
import { useVirtualGrid } from "@web/core/utils/virtual_grid";
const DEFAULT_ROW_HEIGHT = 41; // px — standard Odoo list row
const DEFAULT_GROUP_ROW_HEIGHT = 37; // px — group header row
const DEFAULT_THRESHOLD = 100;
const DEFAULT_BUFFER_COEF = 0.5;

/**
 * @typedef {import("./list_grid_state").FlatRow} FlatRow
 *
 * @typedef ListVirtualizationOptions
 * @property {any} rootRef - ref to .o_list_renderer
 * @property {() => import("./list_grid_state").ListGridState} getGridState
 * @property {() => number} getNbCols - total column count (for spacer colspan)
 * @property {() => boolean} canResequence - whether drag reorder is active
 * @property {() => object | null} getEditedRecord - currently edited record
 * @property {number} [threshold] - min flat rows to activate virtualization
 * @property {number} [bufferCoef] - buffer coefficient for useVirtualGrid
 */

/**
 * @typedef ListVirtualization
 * @property {boolean} isActive - whether virtualization is currently engaged
 * @property {FlatRow[]} visibleFlatRows - slice of flatRows to render
 * @property {number} topSpacerHeight - CSS px for top spacer <tr>
 * @property {number} bottomSpacerHeight - CSS px for bottom spacer <tr>
 * @property {(rowIndex: number) => void} ensureRowVisible - scroll to make a row visible
 * @property {() => void} refresh - recompute visible range (call in onWillRender)
 */

/**
 * Hook providing row virtualization for the list view.
 *
 * @param {ListVirtualizationOptions} options
 * @returns {ListVirtualization}
 */
export function useListVirtualization({
    rootRef,
    getGridState,
    getNbCols,
    canResequence,
    getEditedRecord,
    threshold = DEFAULT_THRESHOLD,
    bufferCoef = DEFAULT_BUFFER_COEF,
}) {
    // Measured row heights (set once from the real DOM on first patched)
    let measuredRowHeight = 0;
    let measuredGroupRowHeight = 0;

    // Current state
    let active = false;
    /** @type {FlatRow[]} */
    let visible = [];
    let topHeight = 0;
    let bottomHeight = 0;
    /** @type {number[]} */
    let heights = [];
    /** @type {number[]} */
    let cumHeights = [];

    const virtualGrid = useVirtualGrid({
        scrollableRef: rootRef,
        bufferCoef,
    });

    /**
     * Measure actual row height from the first rendered data row.
     * Called once after first mount/patch with data rows in the DOM.
     */
    function measureRowHeights() {
        if (measuredRowHeight > 0) {
            return;
        }
        const el = rootRef.el;
        if (!el) {
            return;
        }
        const dataRow = el.querySelector(".o_data_row");
        if (dataRow) {
            measuredRowHeight =
                dataRow.getBoundingClientRect().height || DEFAULT_ROW_HEIGHT;
        }
        const groupRow = el.querySelector(".o_group_header");
        if (groupRow) {
            measuredGroupRowHeight =
                groupRow.getBoundingClientRect().height || DEFAULT_GROUP_ROW_HEIGHT;
        }
    }

    onMounted(measureRowHeights);
    onPatched(measureRowHeights);

    const result = {
        get isActive() {
            return active;
        },
        get visibleFlatRows() {
            return visible;
        },
        get topSpacerHeight() {
            return topHeight;
        },
        get bottomSpacerHeight() {
            return bottomHeight;
        },

        /**
         * Scroll the container to make a given flat row index visible.
         *
         * @param {number} rowIndex - globalIndex in the flat rows array
         */
        ensureRowVisible(rowIndex) {
            if (!active || !rootRef.el) {
                return;
            }
            if (rowIndex < 0 || rowIndex >= cumHeights.length) {
                return;
            }
            const targetTop = rowIndex > 0 ? cumHeights[rowIndex - 1] : 0;
            const containerHeight = rootRef.el.clientHeight;
            // Center the target in the viewport
            const scrollTo = Math.max(0, targetTop - containerHeight / 2);
            rootRef.el.scrollTop = scrollTo;
        },

        /**
         * Recompute the visible range from current grid state.
         * Must be called in onWillRender, after gridState.rebuild().
         */
        refresh() {
            const gridState = getGridState();
            const flatRows = gridState.flatRows;
            const rowCount = flatRows.length;

            // Deactivate when below threshold or when drag-and-drop is active
            if (rowCount <= threshold || canResequence()) {
                active = false;
                visible = [];
                topHeight = 0;
                bottomHeight = 0;
                return;
            }

            active = true;

            // Build heights array
            const rowH = measuredRowHeight || DEFAULT_ROW_HEIGHT;
            const groupH = measuredGroupRowHeight || DEFAULT_GROUP_ROW_HEIGHT;
            heights = new Array(rowCount);
            for (let i = 0; i < rowCount; i++) {
                heights[i] = flatRows[i].type === "group" ? groupH : rowH;
            }

            // Feed heights to the virtual grid engine
            virtualGrid.setRowsHeights(heights);

            const indexes = virtualGrid.rowsIndexes;
            if (!indexes || /** @type {any} */ (indexes).length === 0) {
                // All items fit in viewport (shouldn't happen above threshold, but be safe)
                active = false;
                visible = [];
                topHeight = 0;
                bottomHeight = 0;
                return;
            }

            let [start, end] = indexes;

            // Ensure the edited record is within the visible range
            const editedRecord = getEditedRecord();
            if (editedRecord) {
                const editedRow = gridState.findRowByRecordId(String(editedRecord.id));
                if (editedRow) {
                    const editIdx = editedRow.globalIndex;
                    if (editIdx < start) {
                        start = editIdx;
                    }
                    if (editIdx > end) {
                        end = editIdx;
                    }
                }
            }

            // Clamp
            start = Math.max(0, start);
            end = Math.min(rowCount - 1, end);

            visible = flatRows.slice(start, end + 1);

            // Compute cumulative heights for spacer sizing and ensureRowVisible
            cumHeights = new Array(rowCount);
            let acc = 0;
            for (let i = 0; i < rowCount; i++) {
                acc += heights[i];
                cumHeights[i] = acc;
            }

            topHeight = start > 0 ? cumHeights[start - 1] : 0;
            bottomHeight =
                end < rowCount - 1 ? cumHeights[rowCount - 1] - cumHeights[end] : 0;
        },
    };

    return result;
}
