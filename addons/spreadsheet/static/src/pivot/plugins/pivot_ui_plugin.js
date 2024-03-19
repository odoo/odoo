/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { getFirstPivotFunction, getNumberOfPivotFormulas } from "../pivot_helpers";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { pivotRegistry } from "./pivot_registry";

const { astToFormula } = spreadsheet;

/**
 * @typedef {import("@spreadsheet").Pivot} Pivot
 */

export class PivotUIPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ ([
        "getPivot",
        "getFirstPivotFunction",
        "getPivotIdFromPosition",
        "getPivotDataSourceId",
        "getPivotDomainArgsFromPosition",
        "isPivotUnused",
        "areDomainArgsFieldsValid",
    ]);
    constructor(config) {
        super(config);
        /** @type {Record<string, Pivot} */
        this.pivots = {};
        this.custom = config.custom;
    }

    beforeHandle(cmd) {
        switch (cmd.type) {
            case "START":
                for (const pivotId of this.getters.getPivotIds()) {
                    this._setupPivot(pivotId);
                }
        }
    }

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "REFRESH_PIVOT":
                this._refreshPivot(cmd.id);
                break;
            case "REFRESH_ALL_DATA_SOURCES":
                this._refreshAllPivots();
                break;
            case "ADD_PIVOT": {
                this._setupPivot(cmd.pivotId);
                break;
            }
            case "DUPLICATE_PIVOT": {
                this._setupPivot(cmd.newPivotId);
                break;
            }
            case "UPDATE_ODOO_PIVOT_DOMAIN":
            case "UPDATE_PIVOT": {
                this._setupPivot(cmd.pivotId, { recreate: true });
                break;
            }
            case "DELETE_SHEET":
            case "UPDATE_CELL": {
                this.unusedPivots = undefined;
                break;
            }
            case "UNDO":
            case "REDO": {
                this.unusedPivots = undefined;

                const pivotCommands = cmd.commands.filter((cmd) =>
                    ["ADD_PIVOT", "UPDATE_ODOO_PIVOT_DOMAIN", "UPDATE_PIVOT"].includes(cmd.type)
                );

                for (const cmd of pivotCommands) {
                    if (!this.getters.isExistingPivot(cmd.pivotId)) {
                        continue;
                    }
                    this._setupPivot(cmd.pivotId, { recreate: true });
                }
                break;
            }
        }
    }

    // ---------------------------------------------------------------------
    // Getters
    // ---------------------------------------------------------------------

    /**
     * Get the id of the pivot at the given position. Returns undefined if there
     * is no pivot at this position
     *
     * @param {{ sheetId: string; col: number; row: number}} position
     *
     * @returns {string|undefined}
     */
    getPivotIdFromPosition(position) {
        const cell = this.getters.getCorrespondingFormulaCell(position);
        if (cell && cell.isFormula) {
            const pivotFunction = this.getters.getFirstPivotFunction(cell.compiledFormula.tokens);
            if (pivotFunction) {
                return this.getters.getPivotId(pivotFunction.args[0]?.toString());
            }
        }
        return undefined;
    }

    getFirstPivotFunction(tokens) {
        const pivotFunction = getFirstPivotFunction(tokens);
        if (!pivotFunction) {
            return undefined;
        }
        const { functionName, args } = pivotFunction;
        const evaluatedArgs = args.map((argAst) => {
            if (argAst.type == "EMPTY") {
                return undefined;
            } else if (
                argAst.type === "STRING" ||
                argAst.type === "BOOLEAN" ||
                argAst.type === "NUMBER"
            ) {
                return argAst.value;
            }
            const argsString = astToFormula(argAst);
            return this.getters.evaluateFormula(this.getters.getActiveSheetId(), argsString);
        });
        return { functionName, args: evaluatedArgs };
    }

    /**
     * Returns the domain args of a pivot formula from a position.
     * For all those formulas:
     *
     * =PIVOT.VALUE(1,"expected_revenue","stage_id",2,"city","Brussels")
     * =PIVOT.HEADER(1,"stage_id",2,"city","Brussels")
     * =PIVOT.HEADER(1,"stage_id",2,"city","Brussels","measure","expected_revenue")
     *
     * the result is the same: ["stage_id", 2, "city", "Brussels"]
     *
     * If the cell is the result of PIVOT, the result is the domain of the cell
     * as if it was the individual pivot formula
     *
     * @param {{ col: number, row: number, sheetId: string }} position
     * @returns {(string | number)[] | undefined}
     */
    getPivotDomainArgsFromPosition(position) {
        const cell = this.getters.getCorrespondingFormulaCell(position);
        if (
            !cell ||
            !cell.isFormula ||
            getNumberOfPivotFormulas(cell.compiledFormula.tokens) === 0
        ) {
            return undefined;
        }
        const mainPosition = this.getters.getCellPosition(cell.id);
        const { args, functionName } = this.getters.getFirstPivotFunction(
            cell.compiledFormula.tokens
        );
        if (functionName === "PIVOT") {
            const formulaId = args[0];
            const pivotId = this.getters.getPivotId(formulaId);
            const dataSource = this.getPivot(pivotId);
            if (!pivotId || !dataSource.isReady()) {
                return undefined;
            }
            const includeTotal = args[2];
            const includeColumnHeaders = args[3];
            const pivotCells = dataSource
                .getTableStructure(pivotId)
                .getPivotCells(includeTotal, includeColumnHeaders);
            const pivotCol = position.col - mainPosition.col;
            const pivotRow = position.row - mainPosition.row;
            const pivotCell = pivotCells[pivotCol][pivotRow];
            const domain = pivotCell.domain;
            if (domain?.at(-2) === "measure") {
                return domain.slice(0, -2);
            }
            return domain;
        }
        const domain = args.slice(functionName === "PIVOT.VALUE" ? 2 : 1);
        if (domain.at(-2) === "measure") {
            return domain.slice(0, -2);
        }
        return domain;
    }

    /**
     * @param {string} pivotId
     * @returns {Pivot|undefined}
     */
    getPivot(pivotId) {
        const dataSourceId = this.getPivotDataSourceId(pivotId);
        return this.pivots[dataSourceId];
    }

    getPivotDataSourceId(pivotId) {
        return `pivot-${pivotId}`;
    }

    isPivotUnused(pivotId) {
        return this._getUnusedPivots().includes(pivotId);
    }

    /**
     * Check if the fields in the domain part of
     * a pivot function are valid according to the pivot definition.
     * e.g. =PIVOT.VALUE(1,"revenue","country_id",...,"create_date:month",...,"source_id",...)
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
        const pivot = this.getPivot(pivotId);
        const definition = pivot.definition;
        const cols = definition.columns.map((col) => col.nameWithGranularity);
        const rows = definition.rows.map((row) => row.nameWithGranularity);
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

    // ---------------------------------------------------------------------
    // Private
    // ---------------------------------------------------------------------

    /**
     * Refresh the cache of a pivot
     *
     * @param {string} pivotId Id of the pivot
     */
    _refreshPivot(pivotId) {
        const pivot = this.getters.getPivot(pivotId);
        pivot.load({ reload: true });
    }

    /**
     * Refresh the cache of all the pivots
     */
    _refreshAllPivots() {
        for (const pivotId of this.getters.getPivotIds()) {
            this._refreshPivot(pivotId);
        }
    }

    /**
     * @param {string} pisvotId
     */
    _setupPivot(pivotId, { recreate } = { recreate: false }) {
        const dataSourceId = this.getPivotDataSourceId(pivotId);
        const definition = this.getters.getPivotDefinition(pivotId);
        if (recreate || !(dataSourceId in this.pivots)) {
            const cls = pivotRegistry.get(definition.type);
            this.pivots[dataSourceId] = new cls(this.custom, { definition, getters: this.getters });
        }
    }

    _getUnusedPivots() {
        if (this.unusedPivots !== undefined) {
            return this.unusedPivots;
        }
        const unusedPivots = new Set(this.getters.getPivotIds());
        for (const sheetId of this.getters.getSheetIds()) {
            for (const cellId in this.getters.getCells(sheetId)) {
                const position = this.getters.getCellPosition(cellId);
                const pivotId = this.getPivotIdFromPosition(position);
                if (pivotId) {
                    unusedPivots.delete(pivotId);
                    if (!unusedPivots.size) {
                        this.unusedPivots = [];
                        return [];
                    }
                }
            }
        }
        this.unusedPivots = [...unusedPivots];
        return this.unusedPivots;
    }
}
