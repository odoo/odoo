/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { UIPlugin, tokenize } from "@odoo/o-spreadsheet";
import { getNumberOfPivotFormulas, makePivotFormula } from "@spreadsheet/pivot/pivot_helpers";
import { pivotTimeAdapter } from "@spreadsheet/pivot/pivot_time_adapters";

/**
 * @typedef {import("@spreadsheet/pivot/pivot_table").SpreadsheetPivotTable} SpreadsheetPivotTable
 */

/**
 * @typedef CurrentElement
 * @property {Array<string>} cols
 * @property {Array<string>} rows
 *
 * @typedef TooltipFormula
 * @property {string} value
 *
 * @typedef GroupByDate
 * @property {boolean} isDate
 * @property {string|undefined} group
 */

export class PivotAutofillPlugin extends UIPlugin {
    // ---------------------------------------------------------------------
    // Getters
    // ---------------------------------------------------------------------

    /**
     * Get the next value to autofill of a pivot function
     *
     * @param {string} formula Pivot formula
     * @param {boolean} isColumn True if autofill is LEFT/RIGHT, false otherwise
     * @param {number} increment number of steps
     *
     * @returns {string}
     */
    getPivotNextAutofillValue(formula, isColumn, increment) {
        const tokens = tokenize(formula);
        if (getNumberOfPivotFormulas(tokens) !== 1) {
            return formula;
        }
        const { functionName, args } = this.getters.getFirstPivotFunction(
            this.getters.getActiveSheetId(),
            tokens
        );
        const evaluatedArgs = args.map((arg) => arg.toString());
        const pivotId = evaluatedArgs[0];
        if (!this.getters.isExistingPivot(pivotId)) {
            return formula;
        }
        const dataSource = this.getters.getPivotDataSource(pivotId);
        for (let i = evaluatedArgs.length - 1; i > 0; i--) {
            const fieldName = evaluatedArgs[i];
            if (
                fieldName.startsWith("#") &&
                ((isColumn && dataSource.isColumnGroupBy(fieldName)) ||
                    (!isColumn && dataSource.isRowGroupBy(fieldName)))
            ) {
                evaluatedArgs[i + 1] = parseInt(evaluatedArgs[i + 1], 10) + increment;
                if (evaluatedArgs[i + 1] < 0) {
                    return formula;
                }
                if (functionName === "ODOO.PIVOT") {
                    return makePivotFormula("ODOO.PIVOT", evaluatedArgs);
                } else if (functionName === "ODOO.PIVOT.HEADER") {
                    return makePivotFormula("ODOO.PIVOT.HEADER", evaluatedArgs);
                }
                return formula;
            }
        }
        let builder;
        if (functionName === "ODOO.PIVOT") {
            builder = this._autofillPivotValue.bind(this);
        } else if (functionName === "ODOO.PIVOT.HEADER") {
            if (evaluatedArgs.length === 1) {
                // Total
                if (isColumn) {
                    // LEFT-RIGHT
                    builder = this._autofillPivotRowHeader.bind(this);
                } else {
                    // UP-DOWN
                    builder = this._autofillPivotColHeader.bind(this);
                }
            } else if (
                this.getters.getPivotDefinition(pivotId).rowGroupBys.includes(evaluatedArgs[1])
            ) {
                builder = this._autofillPivotRowHeader.bind(this);
            } else {
                builder = this._autofillPivotColHeader.bind(this);
            }
        }
        if (builder) {
            return builder(pivotId, evaluatedArgs, isColumn, increment);
        }
        return formula;
    }

    /**
     * Compute the tooltip to display from a Pivot formula
     *
     * @param {string} formula Pivot formula
     * @param {boolean} isColumn True if the direction is left/right, false
     *                           otherwise
     *
     * @returns {Array<TooltipFormula>}
     */
    getTooltipFormula(formula, isColumn) {
        const tokens = tokenize(formula);
        if (getNumberOfPivotFormulas(tokens) !== 1) {
            return [];
        }
        const { functionName, args } = this.getters.getFirstPivotFunction(
            this.getters.getActiveSheetId(),
            tokens
        );
        const pivotId = args[0];
        if (!this.getters.isExistingPivot(pivotId)) {
            return [{ title: _t("Missing pivot"), value: _t("Missing pivot #%s", pivotId) }];
        }
        if (functionName === "ODOO.PIVOT") {
            return this._tooltipFormatPivot(pivotId, args, isColumn);
        } else if (functionName === "ODOO.PIVOT.HEADER") {
            return this._tooltipFormatPivotHeader(pivotId, args);
        }
        return [];
    }

    // ---------------------------------------------------------------------
    // Autofill
    // ---------------------------------------------------------------------

    /**
     * Get the next value to autofill from a pivot value ("=PIVOT()")
     *
     * Here are the possibilities:
     * 1) LEFT-RIGHT
     *  - Working on a date value, with one level of group by in the header
     *      => Autofill the date, without taking care of headers
     *  - Targeting a row-header
     *      => Creation of a PIVOT.HEADER with the value of the current rows
     *  - Targeting outside the pivot (before the row header and after the
     *    last col)
     *      => Return empty string
     *  - Targeting a value cell
     *      => Autofill by changing the cols
     * 2) UP-DOWN
     *  - Working on a date value, with one level of group by in the header
     *      => Autofill the date, without taking care of headers
     *  - Targeting a col-header
     *      => Creation of a PIVOT.HEADER with the value of the current cols,
     *         with the given increment
     *  - Targeting outside the pivot (after the last row)
     *      => Return empty string
     *  - Targeting a value cell
     *      => Autofill by changing the rows
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args args of the pivot formula
     * @param {boolean} isColumn True if the direction is left/right, false
     *                           otherwise
     * @param {number} increment Increment of the autofill
     *
     * @private
     *
     * @returns {string}
     */
    _autofillPivotValue(pivotId, args, isColumn, increment) {
        const currentElement = this._getCurrentValueElement(pivotId, args);
        const dataSource = this.getters.getPivotDataSource(pivotId);
        const table = dataSource.getTableStructure();
        const isDate = dataSource.isGroupedOnlyByOneDate(isColumn ? "COLUMN" : "ROW");
        let cols = [];
        let rows = [];
        let measure;
        if (isColumn) {
            // LEFT-RIGHT
            rows = currentElement.rows;
            if (isDate) {
                // Date
                const group = dataSource.getGroupOfFirstDate("COLUMN");
                cols = currentElement.cols;
                cols[0] = this._incrementDate(cols[0], group, increment);
                measure = cols.pop();
            } else {
                const currentColIndex = table.getColMeasureIndex(currentElement.cols);
                if (currentColIndex === -1) {
                    return "";
                }
                const nextColIndex = currentColIndex + increment;
                if (nextColIndex === -1) {
                    // Targeting row-header
                    return this._autofillRowFromValue(pivotId, currentElement);
                }
                if (nextColIndex < -1 || nextColIndex >= table.getNumberOfDataColumns()) {
                    // Outside the pivot
                    return "";
                }
                // Targeting value
                const measureCell = table.getCellFromMeasureRowAtIndex(nextColIndex);
                cols = [...measureCell.values];
                measure = cols.pop();
            }
        } else {
            // UP-DOWN
            cols = currentElement.cols;
            if (isDate) {
                // Date
                if (currentElement.rows.length === 0) {
                    return "";
                }
                const group = dataSource.getGroupOfFirstDate("ROW");
                rows = currentElement.rows;
                rows[0] = this._incrementDate(rows[0], group, increment);
            } else {
                const currentRowIndex = table.getRowIndex(currentElement.rows);
                if (currentRowIndex === -1) {
                    return "";
                }
                const nextRowIndex = currentRowIndex + increment;
                if (nextRowIndex < 0) {
                    // Targeting col-header
                    return this._autofillColFromValue(pivotId, nextRowIndex, currentElement);
                }
                if (nextRowIndex >= table.getNumberOfDataRows()) {
                    // Outside the pivot
                    return "";
                }
                // Targeting value
                rows = [...table.getCellsFromRowAtIndex(nextRowIndex).values];
            }
            measure = cols.pop();
        }
        return makePivotFormula("ODOO.PIVOT", this._buildArgs(pivotId, measure, rows, cols));
    }
    /**
     * Get the next value to autofill from a pivot header ("=PIVOT.HEADER()")
     * which is a col.
     *
     * Here are the possibilities:
     * 1) LEFT-RIGHT
     *  - Working on a date value, with one level of group by in the header
     *      => Autofill the date, without taking care of headers
     *  - Targeting outside (before the first col after the last col)
     *      => Return empty string
     *  - Targeting a col-header
     *      => Creation of a PIVOT.HEADER with the value of the new cols
     * 2) UP-DOWN
     *  - Working on a date value, with one level of group by in the header
     *      => Replace the date in the headers and autocomplete as usual
     *  - Targeting a cell (after the last col and before the last row)
     *      => Autofill by adding the corresponding rows
     *  - Targeting a col-header (after the first col and before the last
     *    col)
     *      => Creation of a PIVOT.HEADER with the value of the new cols
     *  - Targeting outside the pivot (before the first col of after the
     *    last row)
     *      => Return empty string
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args args of the pivot.header formula
     * @param {boolean} isColumn True if the direction is left/right, false
     *                           otherwise
     * @param {number} increment Increment of the autofill
     *
     * @private
     *
     * @returns {string}
     */
    _autofillPivotColHeader(pivotId, args, isColumn, increment) {
        const dataSource = this.getters.getPivotDataSource(pivotId);
        /** @type {SpreadsheetPivotTable} */
        const table = dataSource.getTableStructure();
        const currentElement = this._getCurrentHeaderElement(pivotId, args);
        const currentColIndex = table.getColMeasureIndex(currentElement.cols);
        const isDate = dataSource.isGroupedOnlyByOneDate("COLUMN");
        if (isColumn) {
            // LEFT-RIGHT
            let groupValues;
            if (isDate) {
                // Date
                const group = dataSource.getGroupOfFirstDate("COLUMN");
                groupValues = currentElement.cols;
                groupValues[0] = this._incrementDate(groupValues[0], group, increment);
            } else {
                const rowIndex = currentElement.cols.length - 1;
                const nextColIndex = currentColIndex + increment;
                const nextGroup = table.getNextColCell(nextColIndex, rowIndex);
                if (
                    currentColIndex === -1 ||
                    nextColIndex < 0 ||
                    nextColIndex >= table.getNumberOfDataColumns() ||
                    !nextGroup
                ) {
                    // Outside the pivot
                    return "";
                }
                // Targeting a col.header
                groupValues = nextGroup.values;
            }
            return makePivotFormula(
                "ODOO.PIVOT.HEADER",
                this._buildArgs(pivotId, undefined, [], groupValues)
            );
        } else {
            // UP-DOWN
            const rowIndex =
                currentColIndex === table.getNumberOfDataColumns() - 1
                    ? table.getNumberOfHeaderRows() - 2 + currentElement.cols.length
                    : currentElement.cols.length - 1;
            const nextRowIndex = rowIndex + increment;
            const groupLevels = dataSource.getNumberOfColGroupBys();
            if (nextRowIndex < 0 || nextRowIndex >= groupLevels + 1 + table.getNumberOfDataRows()) {
                // Outside the pivot
                return "";
            }
            if (nextRowIndex >= groupLevels + 1) {
                // Targeting a value
                const rowIndex = nextRowIndex - groupLevels - 1;
                const measureCell = table.getCellFromMeasureRowAtIndex(currentColIndex);
                const cols = [...measureCell.values];
                const measure = cols.pop();
                const rows = [...table.getCellsFromRowAtIndex(rowIndex).values];
                return makePivotFormula(
                    "ODOO.PIVOT",
                    this._buildArgs(pivotId, measure, rows, cols)
                );
            } else {
                // Targeting a col.header
                const groupValues = table.getNextColCell(currentColIndex, nextRowIndex).values;
                return makePivotFormula(
                    "ODOO.PIVOT.HEADER",
                    this._buildArgs(pivotId, undefined, [], groupValues)
                );
            }
        }
    }
    /**
     * Get the next value to autofill from a pivot header ("=PIVOT.HEADER()")
     * which is a row.
     *
     * Here are the possibilities:
     * 1) LEFT-RIGHT
     *  - Targeting outside (LEFT or after the last col)
     *      => Return empty string
     *  - Targeting a cell
     *      => Autofill by adding the corresponding cols
     * 2) UP-DOWN
     *  - Working on a date value, with one level of group by in the header
     *      => Autofill the date, without taking care of headers
     *  - Targeting a row-header
     *      => Creation of a PIVOT.HEADER with the value of the new rows
     *  - Targeting outside the pivot (before the first row of after the
     *    last row)
     *      => Return empty string
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args args of the pivot.header formula
     * @param {boolean} isColumn True if the direction is left/right, false
     *                           otherwise
     * @param {number} increment Increment of the autofill
     *
     * @private
     *
     * @returns {string}
     */
    _autofillPivotRowHeader(pivotId, args, isColumn, increment) {
        const dataSource = this.getters.getPivotDataSource(pivotId);
        const table = dataSource.getTableStructure();
        const currentElement = this._getCurrentHeaderElement(pivotId, args);
        const currentIndex = table.getRowIndex(currentElement.rows);
        const isDate = dataSource.isGroupedOnlyByOneDate("ROW");
        if (isColumn) {
            const colIndex = increment - 1;
            // LEFT-RIGHT
            if (colIndex < 0 || colIndex >= table.getNumberOfDataColumns()) {
                // Outside the pivot
                return "";
            }
            const measureCell = table.getCellFromMeasureRowAtIndex(colIndex);
            const values = [...measureCell.values];
            const measure = values.pop();
            return makePivotFormula(
                "ODOO.PIVOT",
                this._buildArgs(pivotId, measure, currentElement.rows, values)
            );
        } else {
            // UP-DOWN
            let rows;
            if (isDate) {
                // Date
                const group = dataSource.getGroupOfFirstDate("ROW");
                rows = currentElement.rows;
                rows[0] = this._incrementDate(rows[0], group, increment);
            } else {
                const nextIndex = currentIndex + increment;
                if (
                    currentIndex === -1 ||
                    nextIndex < 0 ||
                    nextIndex >= table.getNumberOfDataRows()
                ) {
                    return "";
                }
                rows = [...table.getCellsFromRowAtIndex(nextIndex).values];
            }
            return makePivotFormula(
                "ODOO.PIVOT.HEADER",
                this._buildArgs(pivotId, undefined, rows, [])
            );
        }
    }
    /**
     * Create a col header from a non-header value
     *
     * @param {string} pivotId Id of the pivot
     * @param {number} nextIndex Index of the target column
     * @param {CurrentElement} currentElement Current element (rows and cols)
     *
     * @private
     *
     * @returns {string}
     */
    _autofillColFromValue(pivotId, nextIndex, currentElement) {
        if (nextIndex >= 0) {
            return "";
        }
        const dataSource = this.getters.getPivotDataSource(pivotId);
        const table = dataSource.getTableStructure();
        const groupIndex = table.getColMeasureIndex(currentElement.cols);
        if (groupIndex < 0) {
            return "";
        }
        const isTotalCol = currentElement.cols.length === 1;
        const headerLevels = isTotalCol
            ? 2 // measure and 'Total'
            : dataSource.getNumberOfColGroupBys() + 1; // Groupby levels + measure
        const index = headerLevels + nextIndex;
        if (index < 0) {
            return "";
        }
        const cols = isTotalCol
            ? currentElement.cols.slice(0, index)
            : currentElement.cols.slice(0, index + 1);
        return makePivotFormula("ODOO.PIVOT.HEADER", this._buildArgs(pivotId, undefined, [], cols));
    }
    /**
     * Create a row header from a value
     *
     * @param {string} pivotId Id of the pivot
     * @param {CurrentElement} currentElement Current element (rows and cols)
     *
     * @private
     *
     * @returns {string}
     */
    _autofillRowFromValue(pivotId, currentElement) {
        const rows = currentElement.rows;
        if (!rows) {
            return "";
        }
        return makePivotFormula("ODOO.PIVOT.HEADER", this._buildArgs(pivotId, undefined, rows, []));
    }
    /**
     * Parse the arguments of a pivot function to find the col values and
     * the row values of a PIVOT.HEADER function
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args Args of the pivot.header formula
     *
     * @private
     *
     * @returns {CurrentElement}
     */
    _getCurrentHeaderElement(pivotId, args) {
        const definition = this.getters.getPivotDefinition(pivotId);
        const values = this._parseArgs(args.slice(1));
        const cols = this._getFieldValues([...definition.colGroupBys, "measure"], values);
        const rows = this._getFieldValues(definition.rowGroupBys, values);
        return { cols, rows };
    }
    /**
     * Parse the arguments of a pivot function to find the col values and
     * the row values of a PIVOT function
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args Args of the pivot formula
     *
     * @private
     *
     * @returns {CurrentElement}
     */
    _getCurrentValueElement(pivotId, args) {
        const definition = this.getters.getPivotDefinition(pivotId);
        const values = this._parseArgs(args.slice(2));
        const cols = this._getFieldValues(definition.colGroupBys, values);
        cols.push(args[1]); // measure
        const rows = this._getFieldValues(definition.rowGroupBys, values);
        return { cols, rows };
    }
    /**
     * Return the values for the fields which are present in the list of
     * fields
     *
     * ex: fields: ["create_date"]
     *     values: { create_date: "01/01", stage_id: 1 }
     *      => ["01/01"]
     *
     * @param {Array<string>} fields List of fields
     * @param {Object} values Association field-values
     *
     * @private
     * @returns {Array<string>}
     */
    _getFieldValues(fields, values) {
        return fields.filter((field) => field in values).map((field) => values[field]);
    }
    /**
     * Increment a date with a given increment and interval (group)
     *
     * @param {string} date
     * @param {string} group (day, week, month, ...)
     * @param {number} increment
     *
     * @private
     * @returns {string}
     */
    _incrementDate(date, group, increment) {
        const adapter = pivotTimeAdapter(group);
        const value = adapter.normalizeFunctionValue(date);
        return adapter.increment(value, increment);
    }
    /**
     * Create a structure { field: value } from the arguments of a pivot
     * function
     *
     * @param {Array<string>} args
     *
     * @private
     * @returns {Object}
     */
    _parseArgs(args) {
        const values = {};
        for (let i = 0; i < args.length; i += 2) {
            values[args[i]] = args[i + 1];
        }
        return values;
    }

    // ---------------------------------------------------------------------
    // Tooltips
    // ---------------------------------------------------------------------

    /**
     * Get the tooltip for a pivot formula
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args
     * @param {boolean} isColumn True if the direction is left/right, false
     *                           otherwise
     * @private
     *
     * @returns {Array<TooltipFormula>}
     */
    _tooltipFormatPivot(pivotId, args, isColumn) {
        const tooltips = [];
        const definition = this.getters.getPivotDefinition(pivotId);
        const dataSource = this.getters.getPivotDataSource(pivotId);
        const domain = args.slice(2); // e.g. ["create_date:month", "04/2022", "user_id", 3]
        for (let i = 2; i <= domain.length; i += 2) {
            const fieldName = domain[i - 2];
            if (
                (isColumn && dataSource.isColumnGroupBy(fieldName)) ||
                (!isColumn && dataSource.isRowGroupBy(fieldName))
            ) {
                const formattedValue = this.getters.getPivotHeaderFormattedValue(
                    pivotId,
                    domain.slice(0, i)
                );
                tooltips.push({ value: formattedValue });
            }
        }
        if (definition.measures.length !== 1 && isColumn) {
            const measure = args[1];
            tooltips.push({
                value: dataSource.getMeasureDisplayName(measure),
            });
        }
        if (!tooltips.length) {
            tooltips.push({
                value: _t("Total"),
            });
        }
        return tooltips;
    }
    /**
     * Get the tooltip for a pivot header formula
     *
     * @param {string} pivotId Id of the pivot
     * @param {Array<string>} args
     *
     * @private
     *
     * @returns {Array<TooltipFormula>}
     */
    _tooltipFormatPivotHeader(pivotId, args) {
        const tooltips = [];
        const domain = args.slice(1); // e.g. ["create_date:month", "04/2022", "user_id", 3]
        if (domain.length === 0) {
            return [{ value: _t("Total") }];
        }
        for (let i = 2; i <= domain.length; i += 2) {
            const formattedValue = this.getters.getPivotHeaderFormattedValue(
                pivotId,
                domain.slice(0, i)
            );
            tooltips.push({ value: formattedValue });
        }
        return tooltips;
    }

    // ---------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------

    /**
     * Create the args from pivot, measure, rows and cols
     * if measure is undefined, it's not added
     *
     * @param {string} pivotId Id of the pivot
     * @param {string} measure
     * @param {Object} rows
     * @param {Object} cols
     *
     * @private
     * @returns {Array<string>}
     */
    _buildArgs(pivotId, measure, rows, cols) {
        const { rowGroupBys, measures } = this.getters.getPivotDefinition(pivotId);
        const args = [pivotId];
        if (measure) {
            args.push(measure);
        }
        for (const index in rows) {
            args.push(rowGroupBys[index]);
            args.push(rows[index]);
        }
        if (cols.length === 1 && measures.includes(cols[0])) {
            args.push("measure");
            args.push(cols[0]);
        } else {
            const dataSource = this.getters.getPivotDataSource(pivotId);
            for (const index in cols) {
                args.push(dataSource.getGroupByAtIndex("COLUMN", index) || "measure");
                args.push(cols[index]);
            }
        }
        return args;
    }
}

PivotAutofillPlugin.getters = ["getPivotNextAutofillValue", "getTooltipFormula"];
