// @ts-check

/** @module @web/views/list/list_grid_state - Pure state object materializing flat row arrays for index-based list view grid navigation */

/**
 * Pure JS state object for list view grid navigation.
 *
 * Materializes a flat array of rows (groups + records interleaved) and provides
 * index-based navigation — replacing DOM-walking for arrow key movement.
 * Zero OWL/framework dependency; testable without a browser.
 *
 * Inspired by AG Grid's CellCtrl/RowCtrl separation pattern.
 */

/**
 * @typedef {"group" | "record" | "add-line"} FlatRowType
 *
 * @typedef {{
 *   type: FlatRowType,
 *   globalIndex: number,
 *   record?: object,
 *   group?: object,
 *   parentGroup?: object,
 *   depth: number,
 * }} FlatRow
 */

export class ListGridState {
    /**
     * @param {object} options
     * @param {object} options.list - Odoo list model (DynamicList/StaticList)
     * @param {object[]} options.columns - Active column descriptors
     * @param {boolean} options.hasSelectors - Whether checkbox column is present
     * @param {boolean} options.hasOpenFormViewColumn - Whether "open form" column is present
     * @param {boolean} options.hasActionsColumn - Whether actions column is present
     * @param {boolean} options.isRTL - Right-to-left layout
     * @param {boolean} options.showAddLine - Whether "add a line" rows should be materialized
     * @param {(col: object, rec: object) => boolean} options.isCellReadonly - Readonly check callback
     */
    constructor({
        list,
        columns,
        hasSelectors = false,
        hasOpenFormViewColumn = false,
        hasActionsColumn = false,
        isRTL = false,
        showAddLine = false,
        isCellReadonly = () => false,
    }) {
        this._list = list;
        this._columns = columns;
        this._hasSelectors = hasSelectors;
        this._hasOpenFormViewColumn = hasOpenFormViewColumn;
        this._hasActionsColumn = hasActionsColumn;
        this._isRTL = isRTL;
        this._showAddLine = showAddLine;
        this._isCellReadonly = isCellReadonly;

        /** @type {FlatRow[]} */
        this._flatRows = [];
        /** @type {Map<string, FlatRow>} */
        this._rowByRecordId = new Map();
        /** @type {Map<string, FlatRow>} */
        this._rowByGroupId = new Map();
        /** @type {Map<string, FlatRow>} */
        this._addLineByGroupId = new Map();

        /** Index tracking for cross-row navigation between group and data rows. */
        this._lastColIndex = 0;

        this.rebuild();
    }

    /**
     * Update constructor options before a rebuild (called each render cycle).
     *
     * @param {object} options - Same shape as constructor options (partial OK)
     */
    update(options) {
        if (options.list !== undefined) {
            this._list = options.list;
        }
        if (options.columns !== undefined) {
            this._columns = options.columns;
        }
        if (options.hasSelectors !== undefined) {
            this._hasSelectors = options.hasSelectors;
        }
        if (options.hasOpenFormViewColumn !== undefined) {
            this._hasOpenFormViewColumn = options.hasOpenFormViewColumn;
        }
        if (options.hasActionsColumn !== undefined) {
            this._hasActionsColumn = options.hasActionsColumn;
        }
        if (options.isRTL !== undefined) {
            this._isRTL = options.isRTL;
        }
        if (options.showAddLine !== undefined) {
            this._showAddLine = options.showAddLine;
        }
        if (options.isCellReadonly !== undefined) {
            this._isCellReadonly = options.isCellReadonly;
        }
    }

    /**
     * Rebuild the flat row array from the current list/group state.
     * Call after any structural change (group toggle, page, sort).
     */
    rebuild() {
        this._flatRows = [];
        this._rowByRecordId = new Map();
        this._rowByGroupId = new Map();
        this._addLineByGroupId = new Map();
        this._materialize(this._list, 0, null);
    }

    /** @returns {FlatRow[]} */
    get flatRows() {
        return this._flatRows;
    }

    /** @returns {number} */
    get rowCount() {
        return this._flatRows.length;
    }

    /**
     * Number of navigable columns (field columns + selector + form view + actions).
     *
     * @returns {number}
     */
    get colCount() {
        let count = this._columns.length;
        if (this._hasSelectors) {
            count++;
        }
        if (this._hasOpenFormViewColumn) {
            count++;
        }
        if (this._hasActionsColumn) {
            count++;
        }
        return count;
    }

    /**
     * Find a flat row by record ID.
     *
     * @param {string} recordId
     * @returns {FlatRow | undefined}
     */
    findRowByRecordId(recordId) {
        return this._rowByRecordId.get(recordId);
    }

    /**
     * Find a flat row by group ID.
     *
     * @param {string} groupId
     * @returns {FlatRow | undefined}
     */
    findRowByGroupId(groupId) {
        return this._rowByGroupId.get(groupId);
    }

    /**
     * Find the add-line flat row for a given group ID.
     *
     * @param {string} groupId
     * @returns {FlatRow | undefined}
     */
    findAddLineByGroupId(groupId) {
        return this._addLineByGroupId.get(groupId);
    }

    /**
     * Get the column index for a field name (within the columns array, offset
     * by the selector column if present).
     *
     * @param {string} name
     * @returns {number} -1 if not found
     */
    getColIndexByName(name) {
        const offset = this._hasSelectors ? 1 : 0;
        const idx = this._columns.findIndex((col) => col.name === name);
        return idx === -1 ? -1 : idx + offset;
    }

    /**
     * Index-based focus movement for arrow keys.
     *
     * @param {number} rowIndex
     * @param {number} colIndex
     * @param {"up" | "down" | "left" | "right"} direction
     * @returns {{ rowIndex: number, colIndex: number } | null}
     */
    moveFocus(rowIndex, colIndex, direction) {
        const effectiveDir = this._effectiveDirection(direction);
        switch (effectiveDir) {
            case "up":
                return this._moveVertical(rowIndex, colIndex, -1);
            case "down":
                return this._moveVertical(rowIndex, colIndex, 1);
            case "left":
                return this._moveHorizontal(rowIndex, colIndex, -1);
            case "right":
                return this._moveHorizontal(rowIndex, colIndex, 1);
        }
        return null;
    }

    /**
     * Find the next editable cell starting from (rowIndex, colIndex).
     *
     * @param {number} rowIndex
     * @param {number} colIndex
     * @param {boolean} forward - Search direction
     * @returns {{ rowIndex: number, colIndex: number } | null}
     */
    findNextEditableCell(rowIndex, colIndex, forward = true) {
        const row = this._flatRows[rowIndex];
        if (!row || row.type !== "record") {
            return null;
        }
        const step = forward ? 1 : -1;
        const offset = this._hasSelectors ? 1 : 0;
        let ci = colIndex + step;
        while (ci >= offset && ci < offset + this._columns.length) {
            const col = this._columns[ci - offset];
            if (
                col.type === "field" &&
                row.record &&
                !this._isCellReadonly(col, row.record)
            ) {
                return { rowIndex, colIndex: ci };
            }
            ci += step;
        }
        return null;
    }

    /**
     * Find the first editable cell starting from a column, wrapping around
     * all columns on the same row. Used by focusCell() for edit-mode entry.
     *
     * @param {number} rowIndex
     * @param {number} startColIndex - Column to start searching from (inclusive)
     * @param {boolean} forward - true: search right then wrap; false: search left then wrap
     * @returns {{ rowIndex: number, colIndex: number, column: object } | null}
     */
    findEditableCellWrapping(rowIndex, startColIndex, forward = true) {
        const row = this._flatRows[rowIndex];
        if (!row || row.type !== "record" || !row.record) {
            return null;
        }
        const offset = this._hasSelectors ? 1 : 0;
        const fieldCount = this._columns.length;
        if (fieldCount === 0) {
            return null;
        }
        // Clamp startColIndex into the field column range
        const startFieldIdx = Math.max(
            0,
            Math.min(startColIndex - offset, fieldCount - 1),
        );

        // Build iteration order: from startFieldIdx, wrapping around all columns
        for (let i = 0; i < fieldCount; i++) {
            let fieldIdx;
            if (forward) {
                fieldIdx = (startFieldIdx + i) % fieldCount;
            } else {
                fieldIdx = (startFieldIdx - i + fieldCount) % fieldCount;
            }
            const col = this._columns[fieldIdx];
            if (col.type === "field" && !this._isCellReadonly(col, row.record)) {
                return { rowIndex, colIndex: fieldIdx + offset, column: col };
            }
        }
        return null;
    }

    /**
     * Get the column descriptor at a given colIndex.
     *
     * @param {number} colIndex
     * @returns {object | null}
     */
    getColumnAt(colIndex) {
        const offset = this._hasSelectors ? 1 : 0;
        const fieldIdx = colIndex - offset;
        if (fieldIdx < 0 || fieldIdx >= this._columns.length) {
            return null;
        }
        return this._columns[fieldIdx];
    }

    /**
     * Check whether a cell is editable.
     *
     * @param {number} rowIndex
     * @param {number} colIndex
     * @returns {boolean}
     */
    isCellEditable(rowIndex, colIndex) {
        const row = this._flatRows[rowIndex];
        if (!row || row.type !== "record" || !row.record) {
            return false;
        }
        const offset = this._hasSelectors ? 1 : 0;
        const colArrayIdx = colIndex - offset;
        if (colArrayIdx < 0 || colArrayIdx >= this._columns.length) {
            return false;
        }
        const col = this._columns[colArrayIdx];
        return col.type === "field" && !this._isCellReadonly(col, row.record);
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Recursively walk the list structure, building the flat row array.
     *
     * @param {object} list
     * @param {number} depth
     * @param {object | null} parentGroup
     */
    _materialize(list, depth, parentGroup) {
        if (list.isGrouped) {
            for (const group of list.groups) {
                const groupRow = {
                    type: /** @type {const} */ ("group"),
                    globalIndex: this._flatRows.length,
                    group,
                    parentGroup,
                    depth,
                };
                this._flatRows.push(groupRow);
                this._rowByGroupId.set(String(group.id), groupRow);

                if (!group.isFolded) {
                    this._materialize(group.list, depth + 1, group);
                }
            }
        } else {
            for (const record of list.records) {
                const recordRow = {
                    type: /** @type {const} */ ("record"),
                    globalIndex: this._flatRows.length,
                    record,
                    parentGroup,
                    depth,
                };
                this._flatRows.push(recordRow);
                this._rowByRecordId.set(String(record.id), recordRow);
            }
            // "Add a line" row for editable grouped lists
            if (parentGroup && this._showAddLine) {
                const addLineRow = {
                    type: /** @type {const} */ ("add-line"),
                    globalIndex: this._flatRows.length,
                    parentGroup,
                    depth,
                };
                this._flatRows.push(addLineRow);
                this._addLineByGroupId.set(String(parentGroup.id), addLineRow);
            }
        }
    }

    /**
     * Swap left/right for RTL layouts.
     *
     * @param {"up" | "down" | "left" | "right"} direction
     * @returns {"up" | "down" | "left" | "right"}
     */
    _effectiveDirection(direction) {
        if (!this._isRTL) {
            return direction;
        }
        if (direction === "left") {
            return "right";
        }
        if (direction === "right") {
            return "left";
        }
        return direction;
    }

    /**
     * Move vertically between rows.
     *
     * @param {number} rowIndex
     * @param {number} colIndex
     * @param {number} step - +1 or -1
     * @returns {{ rowIndex: number, colIndex: number } | null}
     */
    _moveVertical(rowIndex, colIndex, step) {
        const nextRowIndex = rowIndex + step;
        if (nextRowIndex < 0 || nextRowIndex >= this._flatRows.length) {
            return null;
        }
        const currentRow = this._flatRows[rowIndex];
        const nextRow = this._flatRows[nextRowIndex];

        // Row-type transition: save/restore column index across group/add-line boundaries
        const currentIsRecord = currentRow.type === "record";
        const nextIsRecord = nextRow.type === "record";
        const nextIsGroup = nextRow.type === "group";

        let targetCol;
        if (currentIsRecord) {
            // Leaving a data record: save current column for later
            this._lastColIndex = colIndex;
        }
        if (nextIsRecord) {
            // Entering a data record: restore saved column if crossing non-record rows
            targetCol = currentIsRecord ? colIndex : this._lastColIndex || 0;
        } else if (nextIsGroup) {
            targetCol = 0; // group headers are single-cell
        } else {
            // add-line or other: preserve column if coming from record,
            // restore saved column otherwise (e.g. group → add-line where
            // colIndex is always 0 — the empty selector placeholder).
            targetCol = currentIsRecord ? colIndex : this._lastColIndex || 0;
        }

        // Clamp to the target row's column count
        // Group headers are single-cell, so colIndex stays 0
        if (nextIsGroup) {
            targetCol = Math.min(targetCol, 0);
        } else {
            targetCol = Math.min(targetCol, this.colCount - 1);
        }

        return { rowIndex: nextRowIndex, colIndex: targetCol };
    }

    /**
     * Move horizontally between columns within the same row.
     *
     * @param {number} rowIndex
     * @param {number} colIndex
     * @param {number} step - +1 or -1
     * @returns {{ rowIndex: number, colIndex: number } | null}
     */
    _moveHorizontal(rowIndex, colIndex, step) {
        const nextCol = colIndex + step;
        if (nextCol < 0 || nextCol >= this.colCount) {
            return null;
        }
        this._lastColIndex = nextCol;
        return { rowIndex, colIndex: nextCol };
    }
}
