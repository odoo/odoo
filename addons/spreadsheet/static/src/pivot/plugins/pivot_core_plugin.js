// @ts-check

/**
 * @typedef {import("@spreadsheet").OdooPivotDefinition} OdooPivotDefinition
 * @typedef {import("@spreadsheet").PivotDefinition} PivotDefinition
 * @typedef {import("@spreadsheet").CorePivotDefinition} CorePivotDefinition
 * @typedef {import("@spreadsheet").AllCoreCommand} AllCoreCommand
 * @typedef {import("@spreadsheet").SPTableCell} SPTableCell
 */

import { helpers, CommandResult as SpreadsheetCommandResult } from "@odoo/o-spreadsheet";
import { makePivotFormula } from "../pivot_helpers";
import { getMaxObjectId } from "@spreadsheet/helpers/helpers";
import { SpreadsheetPivotTable } from "../pivot_table";
import { CommandResult } from "../../o_spreadsheet/cancelled_reason";
import { _t } from "@web/core/l10n/translation";
import { deepCopy } from "@web/core/utils/objects";
import { OdooCorePlugin } from "@spreadsheet/plugins";

const { isDefined, deepEquals } = helpers;

export class PivotCorePlugin extends OdooCorePlugin {
    static getters = /** @type {const} */ ([
        "areDomainArgsFieldsValid",
        "getPivotDefinition",
        "getPivotDisplayName",
        "getPivotId",
        "getPivotFormulaId",
        "getPivotIds",
        "getPivotName",
        "isExistingPivot",
    ]);
    constructor(config) {
        super(config);

        this.nextFormulaId = 1;

        /** @type {Object.<string, CorePivotDefinition>} */
        this.pivots = {};

        /**
         * formulaIds is a mapping between the formula id (the one used
         * in the formulae) and the pivot internal id (pivotId, uuid).
         */
        /** @type {Object<string, string>} */
        this.formulaIds = {};
    }

    /**
     * @param {AllCoreCommand} cmd
     *
     * @returns {string | string[]}
     */
    allowDispatch(cmd) {
        switch (cmd.type) {
            case "UPDATE_PIVOT": {
                if (deepEquals(cmd.pivot, this.pivots[cmd.pivotId])) {
                    return SpreadsheetCommandResult.NoChanges;
                }
                break;
            }
            case "RENAME_PIVOT":
                if (!(cmd.pivotId in this.pivots)) {
                    return CommandResult.PivotIdNotFound;
                }
                if (cmd.name === "") {
                    return CommandResult.EmptyName;
                }
                break;
            case "INSERT_PIVOT": {
                if (!(cmd.pivotId in this.pivots)) {
                    return CommandResult.PivotIdNotFound;
                }
                break;
            }
            case "DUPLICATE_PIVOT":
                if (!(cmd.pivotId in this.pivots)) {
                    return CommandResult.PivotIdNotFound;
                }
        }
        return CommandResult.Success;
    }

    /**
     * @param {AllCoreCommand} cmd
     *
     */
    handle(cmd) {
        switch (cmd.type) {
            case "ADD_PIVOT": {
                const { pivotId, pivot } = cmd;
                this._addPivot(pivotId, pivot);
                break;
            }
            case "INSERT_PIVOT": {
                const { sheetId, col, row, pivotId, table } = cmd;
                /** @type { { col: number, row: number } } */
                const position = { col, row };
                const { cols, rows, measures, rowTitle } = table;
                const spTable = new SpreadsheetPivotTable(cols, rows, measures, rowTitle);
                const formulaId = this.getPivotFormulaId(pivotId);
                this._insertPivot(sheetId, position, formulaId, spTable);
                break;
            }
            case "RENAME_PIVOT": {
                this.history.update("pivots", cmd.pivotId, "name", cmd.name);
                break;
            }
            case "REMOVE_PIVOT": {
                const pivots = { ...this.pivots };
                delete pivots[cmd.pivotId];
                const formulaId = this.getPivotFormulaId(cmd.pivotId);
                this.history.update("formulaIds", formulaId, undefined);
                this.history.update("pivots", pivots);
                break;
            }
            case "DUPLICATE_PIVOT": {
                const { pivotId, newPivotId } = cmd;
                const pivot = deepCopy(this.pivots[pivotId]);
                this._addPivot(newPivotId, pivot);
                break;
            }
            // this command is deprecated. use UPDATE_PIVOT instead
            case "UPDATE_ODOO_PIVOT_DOMAIN": {
                this.history.update("pivots", cmd.pivotId, "domain", cmd.domain);
                break;
            }
            case "UPDATE_PIVOT": {
                this.history.update("pivots", cmd.pivotId, cmd.pivot);
                break;
            }
        }
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /**
     * @param {string} id
     * @returns {string}
     */
    getPivotDisplayName(id) {
        const formulaId = this.getPivotFormulaId(id);
        return `(#${formulaId}) ${this.getPivotName(id)}`;
    }

    /**
     * @param {string} id
     * @returns {string}
     */
    getPivotName(id) {
        return _t(this.pivots[id].name);
    }

    /**
     * @param {string} id Id of the pivot
     *
     * @returns {PivotDefinition}
     */
    getPivotDefinition(id) {
        return this.pivots[id];
    }

    /**
     * Get the pivot ID from the one used in a PIVOT formula.
     *
     * @param {string} formulaId
     * @returns {string | undefined}
     */
    getPivotId(formulaId) {
        return this.formulaIds[formulaId];
    }

    /**
     * Get the pivot formula id (the one used in a PIVOT formula) from a pivot id
     * @param {string} pivotId
     * @returns {string|undefined}
     */
    getPivotFormulaId(pivotId) {
        return this.pivots[pivotId]?.formulaId;
    }

    /**
     * Retrieve all the pivot ids
     *
     * @returns {Array<string>}
     */
    getPivotIds() {
        return Object.keys(this.pivots);
    }

    /**
     * Check if an id is an id of an existing pivot
     *
     * @param {number | string} pivotId Id of the pivot
     *
     * @returns {boolean}
     */
    isExistingPivot(pivotId) {
        return pivotId in this.pivots;
    }

    /**
     * Check if the fields in the domain part of
     * a pivot function are valid according to the pivot definition.
     * e.g. =ODOO.PIVOT(1,"revenue","country_id",...,"create_date:month",...,"source_id",...)
     * @param {string} pivotId
     * @param {string[]} domainArgs
     * @returns {boolean}
     */
    areDomainArgsFieldsValid(pivotId, domainArgs) {
        const dimensions = domainArgs
            .filter((arg, index) => index % 2 === 0)
            .map((name) => (name.startsWith("#") ? name.slice(1) : name));
        let argIndex = 0;
        let definitionIndex = 0;
        const definition = this.getPivotDefinition(pivotId);
        const cols = definition.colGroupBys;
        const rows = definition.rowGroupBys;
        while (
            dimensions[argIndex] !== undefined &&
            dimensions[argIndex] === rows[definitionIndex]
        ) {
            argIndex++;
            definitionIndex++;
        }
        definitionIndex = 0;
        while (
            dimensions[argIndex] !== undefined &&
            dimensions[argIndex] === cols[definitionIndex]
        ) {
            argIndex++;
            definitionIndex++;
        }
        return dimensions.length === argIndex;
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * @param {string} id
     * @param {PivotDefinition} pivot
     * @param {string} formulaId
     */
    _addPivot(id, pivot, formulaId = this.nextFormulaId.toString()) {
        const pivots = { ...this.pivots };
        pivots[id] = {
            ...pivot,
            formulaId,
        };
        this.history.update("pivots", pivots);
        this.history.update("formulaIds", formulaId, id);
        this.history.update("nextFormulaId", this.nextFormulaId + 1);
    }

    /**
     * @param {string} sheetId
     * @param {{ col: number, row: number }} position
     * @param {string} id
     * @param {SpreadsheetPivotTable} table
     */
    _insertPivot(sheetId, position, id, table) {
        this._resizeSheet(sheetId, position, table);
        const pivotCells = table.getPivotCells();
        for (let col = 0; col < pivotCells.length; col++) {
            for (let row = 0; row < pivotCells[col].length; row++) {
                const pivotCell = pivotCells[col][row];
                const functionCol = position.col + col;
                const functionRow = position.row + row;
                this._addPivotFormula(
                    sheetId,
                    id,
                    { col: functionCol, row: functionRow },
                    pivotCell
                );
            }
        }

        this._addBorders(sheetId, position, table);
    }

    /**
     * @param {string} sheetId
     * @param {{ col: number, row: number }} position
     * @param {SpreadsheetPivotTable} table
     */
    _resizeSheet(sheetId, { col, row }, table) {
        const colLimit = table.getNumberOfDataColumns() + 1; // +1 for the Top-Left
        const numberCols = this.getters.getNumberCols(sheetId);
        const deltaCol = numberCols - col;
        if (deltaCol < colLimit) {
            this.dispatch("ADD_COLUMNS_ROWS", {
                dimension: "COL",
                base: numberCols - 1,
                sheetId: sheetId,
                quantity: colLimit - deltaCol,
                position: "after",
            });
        }
        const rowLimit = table.getNumberOfHeaderRows() + table.getNumberOfDataRows();
        const numberRows = this.getters.getNumberRows(sheetId);
        const deltaRow = numberRows - row;
        if (deltaRow < rowLimit) {
            this.dispatch("ADD_COLUMNS_ROWS", {
                dimension: "ROW",
                base: numberRows - 1,
                sheetId: sheetId,
                quantity: rowLimit - deltaRow,
                position: "after",
            });
        }
    }

    /**
     * @param {string} sheetId
     * @param {{ col: number, row: number }} position
     * @param {SpreadsheetPivotTable} table
     */
    _addBorders(sheetId, { col, row }, table) {
        const colHeight = table.getNumberOfHeaderRows();
        const colWidth = table.getNumberOfDataColumns();
        const totalRow = row + colHeight + table.getRowHeaders().length - 1;
        const headerAndMeasureZone = {
            top: row,
            bottom: row + colHeight - 1,
            left: col,
            right: col + colWidth,
        };
        this.dispatch("SET_ZONE_BORDERS", {
            sheetId,
            target: [
                headerAndMeasureZone,
                {
                    left: col,
                    right: col + colWidth,
                    top: totalRow,
                    bottom: totalRow,
                },
                {
                    left: col,
                    right: col + colWidth,
                    top: row,
                    bottom: totalRow,
                },
            ],
            border: {
                position: "external",
                color: "#2D7E84",
            },
        });
    }

    /**
     * @param {string} sheetId
     * @param {string} pivotId
     * @param {{ col: number, row: number }} position
     * @param {SPTableCell} pivotCell
     */
    _addPivotFormula(sheetId, pivotId, { col, row }, pivotCell) {
        const formula = pivotCell.isHeader ? "ODOO.PIVOT.HEADER" : "ODOO.PIVOT";
        const args = pivotCell.domain
            ? [pivotId, pivotCell.measure, ...pivotCell.domain].filter(isDefined)
            : undefined;

        this.dispatch("UPDATE_CELL", {
            sheetId,
            col,
            row,
            content: pivotCell.content || (args ? makePivotFormula(formula, args) : undefined),
            style: pivotCell.style,
        });
    }

    // ---------------------------------------------------------------------
    // Import/Export
    // ---------------------------------------------------------------------

    /**
     * Import the pivots
     *
     * @param {Object} data
     */
    import(data) {
        if (data.pivots) {
            for (const [id, pivot] of Object.entries(data.pivots)) {
                this._addPivot(id, deepCopy(pivot), pivot.formulaId);
            }
        }
        this.nextFormulaId = data.pivotNextId || getMaxObjectId(this.pivots) + 1;
    }
    /**
     * Export the pivots
     *
     * @param {Object} data
     */
    export(data) {
        data.pivots = {};
        for (const id in this.pivots) {
            data.pivots[id] = deepCopy(this.pivots[id]);
        }
        data.pivotNextId = this.nextFormulaId;
    }
}
