import { _t } from "@web/core/l10n/translation";
import { UIPlugin, tokenize, helpers } from "@odoo/o-spreadsheet";
import { domainHasNoRecordAtThisPosition } from "@spreadsheet/pivot/pivot_helpers";

const { getNumberOfPivotFunctions, isDateOrDatetimeField, pivotTimeAdapter, createPivotFormula } =
    helpers;

/**
 * @typedef {import("@odoo/o-spreadsheet").SpreadsheetPivotTable} SpreadsheetPivotTable
 * @typedef {import("@spreadsheet").OdooPivotDefinition} OdooPivotDefinition
 * @typedef {import("@spreadsheet/pivot/odoo_pivot").OdooPivot} OdooPivot
 * @typedef {import("@spreadsheet/pivot/odoo_pivot").PivotDomain} PivotDomain
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
        if (getNumberOfPivotFunctions(tokens) !== 1) {
            return formula;
        }
        const { functionName, args } = this.getters.getFirstPivotFunction(
            this.getters.getActiveSheetId(),
            tokens
        );
        if (args.some((arg) => arg === undefined)) {
            return formula;
        }
        const evaluatedArgs = args.map((arg) => arg.toString());
        const pivotId = this.getters.getPivotId(evaluatedArgs[0]);
        if (!pivotId) {
            return formula;
        }
        const dataSource = this.getters.getPivot(pivotId);
        const definition = dataSource.definition;
        for (let i = evaluatedArgs.length - 1; i > 0; i--) {
            const fieldName = evaluatedArgs[i];
            if (
                fieldName.startsWith("#") &&
                ((isColumn && this._isColumnGroupBy(dataSource, definition, fieldName)) ||
                    (!isColumn && this._isRowGroupBy(dataSource, definition, fieldName)))
            ) {
                evaluatedArgs[i + 1] = parseInt(evaluatedArgs[i + 1], 10) + increment;
                if (evaluatedArgs[i + 1] < 0) {
                    return formula;
                }
                if (functionName === "PIVOT.VALUE") {
                    const [formulaId, measure, ...domain] = evaluatedArgs;
                    const pivotCell = {
                        type: "VALUE",
                        measure,
                        domain: this._toPivotDomainWithPositional(dataSource, domain),
                    };
                    return createPivotFormula(formulaId, pivotCell);
                } else if (functionName === "PIVOT.HEADER") {
                    const [formulaId, ...domain] = evaluatedArgs;
                    const pivotCell = {
                        type: "HEADER",
                        domain: this._toPivotDomainWithPositional(dataSource, domain),
                    };
                    return createPivotFormula(formulaId, pivotCell);
                }
                return formula;
            }
        }
        let builder;
        if (functionName === "PIVOT.VALUE") {
            builder = this._autofillPivotValue.bind(this);
        } else if (functionName === "PIVOT.HEADER") {
            const nonPositionalArgs = evaluatedArgs.map((arg) =>
                arg.startsWith("#") ? arg.slice(1) : arg
            );
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
                definition.rows.map((row) => row.nameWithGranularity).includes(nonPositionalArgs[1])
            ) {
                builder = this._autofillPivotRowHeader.bind(this);
            } else {
                builder = this._autofillPivotColHeader.bind(this);
            }
        }
        if (builder) {
            return builder(pivotId, evaluatedArgs, isColumn, increment, dataSource, definition);
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
        if (getNumberOfPivotFunctions(tokens) !== 1) {
            return [];
        }
        const { functionName, args } = this.getters.getFirstPivotFunction(
            this.getters.getActiveSheetId(),
            tokens
        );
        const pivotId = this.getters.getPivotId(args[0]);
        if (!pivotId) {
            return [{ title: _t("Missing pivot"), value: _t("Missing pivot #%s", args[0]) }];
        }
        if (functionName === "PIVOT.VALUE") {
            const dataSource = this.getters.getPivot(pivotId);
            const definition = dataSource.definition;
            return this._tooltipFormatPivot(args, isColumn, dataSource, definition);
        } else if (functionName === "PIVOT.HEADER") {
            const dataSource = this.getters.getPivot(pivotId);
            return this._tooltipFormatPivotHeader(args, dataSource);
        }
        return [];
    }

    // ---------------------------------------------------------------------
    // Autofill
    // ---------------------------------------------------------------------

    /**
     * Get the next value to autofill from a pivot value ("=PIVOT.VALUE()")
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
     * @param {OdooPivot} dataSource
     * @param {OdooPivotDefinition} definition
     *
     * @private
     *
     * @returns {string}
     */
    _autofillPivotValue(pivotId, args, isColumn, increment, dataSource, definition) {
        const currentElement = this._getCurrentValueElement(args, definition);
        const table = dataSource.getTableStructure();
        const isDate = this._isGroupedOnlyByOneDate(definition, isColumn ? "COLUMN" : "ROW");
        let cols = [];
        let rows = [];
        let measure;
        if (isColumn) {
            // LEFT-RIGHT
            rows = currentElement.rows;
            if (isDate && currentElement.cols.length > 1) {
                // Date
                const group = this._getGroupOfFirstDate(definition, "COLUMN");
                cols = currentElement.cols;
                const value = this._incrementDate(cols[0], group, increment);
                if (value === undefined) {
                    return "";
                }
                cols[0] = value;
                measure = cols.pop();
            } else {
                const currentColIndex = this._getColMeasureIndex(table, currentElement.cols);
                if (currentColIndex === -1) {
                    return "";
                }
                const nextColIndex = currentColIndex + increment;
                if (nextColIndex === -1) {
                    // Targeting row-header
                    return this._autofillRowFromValue(pivotId, currentElement, definition);
                }
                if (nextColIndex < -1 || nextColIndex >= table.getNumberOfDataColumns()) {
                    // Outside the pivot
                    return "";
                }
                // Targeting value
                const measureCell = this._getCellFromMeasureRowAtIndex(table, nextColIndex);
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
                const group = this._getGroupOfFirstDate(definition, "ROW");
                rows = currentElement.rows;
                const value = this._incrementDate(rows[0], group, increment);
                if (value === undefined) {
                    return "";
                }
                rows[0] = value;
            } else {
                const currentRowIndex = this._getRowIndex(table, currentElement.rows);
                if (currentRowIndex === -1) {
                    return "";
                }
                const nextRowIndex = currentRowIndex + increment;
                if (nextRowIndex < 0) {
                    // Targeting col-header
                    return this._autofillColFromValue(
                        pivotId,
                        nextRowIndex,
                        currentElement,
                        dataSource,
                        definition
                    );
                }
                if (nextRowIndex >= table.rows.length) {
                    // Outside the pivot
                    return "";
                }
                // Targeting value
                rows = [...this._getCellsFromRowAtIndex(table, nextRowIndex).values];
            }
            measure = cols.pop();
        }
        return this._createPivotFormula(pivotId, rows, cols, definition, measure);
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
     * @param {OdooPivot} dataSource
     * @param {OdooPivotDefinition} definition
     *
     * @private
     *
     * @returns {string}
     */
    _autofillPivotColHeader(pivotId, args, isColumn, increment, dataSource, definition) {
        /** @type {SpreadsheetPivotTable} */
        const table = dataSource.getTableStructure();
        const currentElement = this._getCurrentHeaderElement(args, definition);
        const currentColIndex = this._getColMeasureIndex(table, currentElement.cols);
        const isDate =
            this._isGroupedOnlyByOneDate(definition, "COLUMN") &&
            currentColIndex !== table.getNumberOfDataColumns() - 1;
        if (isColumn) {
            // LEFT-RIGHT
            let groupValues;
            if (isDate) {
                // Date
                const group = this._getGroupOfFirstDate(definition, "COLUMN");
                groupValues = currentElement.cols;
                const value = this._incrementDate(groupValues[0], group, increment);
                if (value === undefined) {
                    return "";
                }
                groupValues[0] = value;
            } else {
                const rowIndex = currentElement.cols.length - 1;
                const nextColIndex = currentColIndex + increment;
                const nextGroup = this._getNextColCell(table, nextColIndex, rowIndex);
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
            return this._createPivotFormula(pivotId, [], groupValues, definition);
        } else {
            // UP-DOWN
            const rowIndex =
                currentColIndex === table.getNumberOfDataColumns() - 1
                    ? table.columns.length - 2 + currentElement.cols.length
                    : currentElement.cols.length - 1;
            const nextRowIndex = rowIndex + increment;
            const groupLevels = this._getNumberOfColGroupBys(definition);
            if (nextRowIndex < 0 || nextRowIndex >= groupLevels + 1 + table.rows.length) {
                // Outside the pivot
                return "";
            }
            if (nextRowIndex >= groupLevels + 1) {
                // Targeting a value
                const rowIndex = nextRowIndex - groupLevels - 1;
                let cols;
                if (currentColIndex >= 0) {
                    cols = [...this._getCellFromMeasureRowAtIndex(table, currentColIndex).values];
                } else if (groupLevels > 1) {
                    return "";
                } else {
                    // Autofilling value not present in the original table
                    cols = [
                        ...currentElement.cols,
                        ...this._getCellFromMeasureRowAtIndex(table, 0).values.slice(
                            currentElement.cols.length
                        ),
                    ];
                }
                const measure = cols.pop();
                const rows = [...this._getCellsFromRowAtIndex(table, rowIndex).values];
                return this._createPivotFormula(pivotId, rows, cols, definition, measure);
            } else {
                // Targeting a col.header
                let groupValues;
                if (currentColIndex >= 0) {
                    groupValues = this._getNextColCell(table, currentColIndex, nextRowIndex).values;
                } else if (groupLevels > 1) {
                    return "";
                } else {
                    // Autofilling value not present in the original table
                    groupValues = [
                        ...currentElement.cols,
                        ...this._getNextColCell(table, 0, nextRowIndex).values.slice(
                            currentElement.cols.length
                        ),
                    ];
                }
                return this._createPivotFormula(pivotId, [], groupValues, definition);
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
     * @param {OdooPivot} dataSource
     * @param {OdooPivotDefinition} definition
     *
     * @private
     *
     * @returns {string}
     */
    _autofillPivotRowHeader(pivotId, args, isColumn, increment, dataSource, definition) {
        const table = dataSource.getTableStructure();
        const currentElement = this._getCurrentHeaderElement(args, definition);
        const currentIndex = this._getRowIndex(table, currentElement.rows);
        const isDate = this._isGroupedOnlyByOneDate(definition, "ROW");
        if (isColumn) {
            const colIndex = increment - 1;
            // LEFT-RIGHT
            if (colIndex < 0 || colIndex >= table.getNumberOfDataColumns()) {
                // Outside the pivot
                return "";
            }
            const measureCell = this._getCellFromMeasureRowAtIndex(table, colIndex);
            const values = [...measureCell.values];
            const measure = values.pop();
            return this._createPivotFormula(
                pivotId,
                currentElement.rows,
                values,
                definition,
                measure
            );
        } else {
            // UP-DOWN
            let rows;
            if (isDate) {
                // Date
                const group = this._getGroupOfFirstDate(definition, "ROW");
                rows = currentElement.rows;
                const value = this._incrementDate(rows[0], group, increment);
                if (value === undefined) {
                    return "";
                }
                rows[0] = value;
            } else {
                const nextIndex = currentIndex + increment;
                if (currentIndex === -1 || nextIndex < 0 || nextIndex >= table.rows.length) {
                    return "";
                }
                rows = [...this._getCellsFromRowAtIndex(table, nextIndex).values];
            }
            return this._createPivotFormula(pivotId, rows, [], definition);
        }
    }
    /**
     * Create a col header from a non-header value
     *
     * @param {string} pivotId Id of the pivot
     * @param {number} nextIndex Index of the target column
     * @param {CurrentElement} currentElement Current element (rows and cols)
     * @param {OdooPivot} dataSource
     * @param {OdooPivotDefinition} definition
     *
     * @private
     *
     * @returns {string}
     */
    _autofillColFromValue(pivotId, nextIndex, currentElement, dataSource, definition) {
        if (nextIndex >= 0) {
            return "";
        }
        const table = dataSource.getTableStructure();
        const groupIndex = this._getColMeasureIndex(table, currentElement.cols);
        if (groupIndex < 0) {
            return "";
        }
        const isTotalCol = currentElement.cols.length === 1;
        const headerLevels = isTotalCol
            ? 2 // measure and 'Total'
            : this._getNumberOfColGroupBys(definition) + 1; // Groupby levels + measure
        const index = headerLevels + nextIndex;
        if (index < 0) {
            return "";
        }
        const cols = isTotalCol
            ? currentElement.cols.slice(0, index)
            : currentElement.cols.slice(0, index + 1);
        return this._createPivotFormula(pivotId, [], cols, definition);
    }
    /**
     * Create a row header from a value
     *
     * @param {string} pivotId Id of the pivot
     * @param {CurrentElement} currentElement Current element (rows and cols)
     * @param {OdooPivotDefinition} definition
     *
     * @private
     *
     * @returns {string}
     */
    _autofillRowFromValue(pivotId, currentElement, definition) {
        const rows = currentElement.rows;
        if (!rows) {
            return "";
        }
        return this._createPivotFormula(pivotId, rows, [], definition);
    }
    /**
     * Parse the arguments of a pivot function to find the col values and
     * the row values of a PIVOT.HEADER function
     *
     * @param {Array<string>} args Args of the pivot.header formula
     * @param {OdooPivotDefinition} definition
     *
     * @private
     *
     * @returns {CurrentElement}
     */
    _getCurrentHeaderElement(args, definition) {
        const values = this._parseArgs(args.slice(1));
        const cols = this._getFieldValues(
            [...definition.columns.map((col) => col.nameWithGranularity), "measure"],
            values
        );
        const rows = this._getFieldValues(
            definition.rows.map((row) => row.nameWithGranularity),
            values
        );
        return { cols, rows };
    }
    /**
     * Parse the arguments of a pivot function to find the col values and
     * the row values of a PIVOT function
     *
     * @param {Array<string>} args Args of the pivot formula
     * @param {OdooPivotDefinition} definition
     *
     * @private
     *
     * @returns {CurrentElement}
     */
    _getCurrentValueElement(args, definition) {
        const values = this._parseArgs(args.slice(2));
        const cols = this._getFieldValues(
            definition.columns.map((col) => col.nameWithGranularity),
            values
        );
        cols.push(args[1]); // measure
        const rows = this._getFieldValues(
            definition.rows.map((row) => row.nameWithGranularity),
            values
        );
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
     * @param {OdooPivot} dataSource
     * @param {OdooPivotDefinition} definition
     *
     * @private
     *
     * @returns {Array<TooltipFormula>}
     */
    _tooltipFormatPivot(args, isColumn, dataSource, definition) {
        const tooltips = [];
        const domain = args.slice(2);
        for (let i = 0; i < domain.length; i += 2) {
            if (
                (isColumn && this._isColumnGroupBy(dataSource, definition, domain[i])) ||
                (!isColumn && this._isRowGroupBy(dataSource, definition, domain[i]))
            ) {
                tooltips.push(this._tooltipHeader(dataSource, domain.slice(0, i + 2)));
            }
        }
        if (definition.measures.length !== 1 && isColumn) {
            const measure = args[1];
            tooltips.push({
                value: dataSource.getMeasure(measure).displayName,
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
     * @param {string} pivotId
     * @param {Array<string>} args
     * @param {OdooPivot} dataSource
     *
     * @private
     *
     * @returns {Array<TooltipFormula>}
     */
    _tooltipFormatPivotHeader(args, dataSource) {
        const tooltips = [];
        const domain = args.slice(1).map((value) => ({ value }));
        if (domain.length === 0) {
            return [{ value: _t("Total") }];
        }

        for (let i = 0; i < domain.length; i += 2) {
            tooltips.push(this._tooltipHeader(dataSource, domain.slice(0, i + 2)));
        }
        return tooltips;
    }

    _tooltipHeader(dataSource, domain) {
        const subDomain = dataSource.parseArgsToPivotDomain(domain);
        if (!domainHasNoRecordAtThisPosition(subDomain)) {
            const formattedValue = this._getPivotHeaderFormattedValue(dataSource, subDomain);
            return { value: formattedValue };
        } else {
            return { value: "" };
        }
    }

    _getPivotHeaderFormattedValue(dataSource, domain) {
        try {
            return dataSource.getPivotHeaderFormattedValue(domain);
        } catch {
            return _t("Unknown");
        }
    }

    // ---------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------

    _toPivotDomainWithPositional(pivot, args) {
        const domain = [];
        for (let i = 0; i < args.length - 1; i += 2) {
            const fullName = args[i];
            const { field, isPositional } = pivot.parseGroupField(fullName);
            domain.push({
                field: fullName,
                value: args[i + 1],
                type: isPositional ? "integer" : field.type,
            });
        }
        return domain;
    }

    /**
     * Create a pivot formula
     *
     * @param {string} pivotId
     * @param {Object} rows
     * @param {Object} cols
     * @param {OdooPivotDefinition} definition
     * @param {string} [measure]
     *
     * @returns {string}
     */
    _createPivotFormula(pivotId, rows, cols, definition, measure) {
        /** @type {PivotDomain} */
        const domain = [];
        for (const index in rows) {
            const row = definition.rows[index];
            domain.push({
                type: row.type,
                field: row.nameWithGranularity,
                value: rows[index],
            });
        }
        if (cols.length === 1 && definition.measures.map((m) => m.id).includes(cols[0])) {
            domain.push({
                type: "char",
                field: "measure",
                value: cols[0],
            });
        } else {
            for (const index in cols) {
                const column = definition.columns[index] || {
                    type: "char",
                    nameWithGranularity: "measure",
                };
                domain.push({
                    type: column.type,
                    field: column.nameWithGranularity,
                    value: cols[index],
                });
            }
        }
        const pivotCell = {
            type: measure ? "VALUE" : "HEADER",
            measure,
            domain,
        };
        const formulaId = this.getters.getPivotFormulaId(pivotId);
        return createPivotFormula(formulaId, pivotCell);
    }

    /**
     * @param {OdooPivotDefinition} definition
     * @param {string} dimension COLUMN | ROW
     */
    _isGroupedOnlyByOneDate(definition, dimension) {
        const groupBys = dimension === "COLUMN" ? definition.columns : definition.rows;
        return groupBys.length === 1 && isDateOrDatetimeField(groupBys[0]);
    }
    /**
     * @param {OdooPivotDefinition} definition
     * @param {string} dimension COLUMN | ROW
     */
    _getGroupOfFirstDate(definition, dimension) {
        if (!this._isGroupedOnlyByOneDate(definition, dimension)) {
            return undefined;
        }
        const groupBys = dimension === "COLUMN" ? definition.columns : definition.rows;
        return groupBys[0].granularity || "month";
    }

    /**
     * @param {OdooPivotDefinition} definition
     * @returns {number}
     */
    _getNumberOfColGroupBys(definition) {
        return definition.columns.length;
    }

    /**
     * @param {OdooPivot} dataSource
     * @param {OdooPivotDefinition} definition
     * @param {string} fieldName
     * @returns {boolean}
     */
    _isColumnGroupBy(dataSource, definition, fieldName) {
        const name = dataSource.parseGroupField(fieldName).field.name;
        return definition.columns.map((col) => col.fieldName).includes(name);
    }

    /**
     * @param {OdooPivot} dataSource
     * @param {OdooPivotDefinition} definition
     * @param {string} fieldName
     * @returns {boolean}
     */
    _isRowGroupBy(dataSource, definition, fieldName) {
        const name = dataSource.parseGroupField(fieldName).field.name;
        return definition.rows.map((row) => row.fieldName).includes(name);
    }

    _getColMeasureIndex(table, values) {
        const vals = JSON.stringify(values);
        const maxLength = Math.max(...table.columns.map((col) => col.length));
        for (let i = 0; i < maxLength; i++) {
            const cellValues = table.columns.map((col) => JSON.stringify((col[i] || {}).values));
            if (cellValues.includes(vals)) {
                return i;
            }
        }
        return -1;
    }

    _getNextColCell(table, colIndex, rowIndex) {
        return table.columns[rowIndex][colIndex];
    }

    _getRowIndex(table, values) {
        const vals = JSON.stringify(values);
        return table.rows.findIndex(
            (cell) => JSON.stringify(cell.values.map((val) => val.toString())) === vals
        );
    }

    _getCellFromMeasureRowAtIndex(table, index) {
        return table.columns.at(-1)[index];
    }

    _getCellsFromRowAtIndex(table, index) {
        return table.rows[index];
    }
}

PivotAutofillPlugin.getters = ["getPivotNextAutofillValue", "getTooltipFormula"];
