/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { getFirstPivotFunction, getNumberOfPivotFormulas } from "../pivot_helpers";
import { OdooPivot } from "../pivot_data_source";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { pivotTimeAdapter } from "../pivot_time_adapters";

const { astToFormula, helpers } = spreadsheet;
const { formatValue } = helpers;

/**
 * @typedef {import("./pivot_core_plugin").OdooPivotDefinition} OdooPivotDefinition
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").FieldMatching} FieldMatching
 * @typedef {import("@odoo/o-spreadsheet").Token} Token
 */

export class PivotUIPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ ([
        "getPivot",
        "getFirstPivotFunction",
        "computePivotHeaderValue",
        "getPivotHeaderFormattedValue",
        "getPivotFieldFormat",
        "getPivotIdFromPosition",
        "getPivotCellValue",
        "getPivotGroupByValues",
        "getPivotDataSourceId",
        "getPivotTableStructure",
        "getPivotDomainArgsFromPosition",
        "isPivotUnused",
    ]);
    constructor(config) {
        super(config);
        this.dataSources = config.custom.dataSources;
    }

    beforeHandle(cmd) {
        switch (cmd.type) {
            case "START":
                for (const pivotId of this.getters.getPivotIds()) {
                    this._setupPivotDataSource(pivotId);
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
                this._refreshOdooPivot(cmd.id);
                break;
            case "REFRESH_ALL_DATA_SOURCES":
                this._refreshOdooPivots();
                break;
            case "ADD_PIVOT": {
                const { id } = cmd;
                this._setupPivotDataSource(id);
                break;
            }
            case "DUPLICATE_PIVOT": {
                const { newPivotId } = cmd;
                this._setupPivotDataSource(newPivotId);
                break;
            }
            case "UPDATE_ODOO_PIVOT_DOMAIN": {
                const pivotDefinition = this.getters.getPivotDefinition(cmd.pivotId);
                const dataSourceId = this.getPivotDataSourceId(cmd.pivotId);
                this.dataSources.add(dataSourceId, OdooPivot, pivotDefinition);
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

                const domainEditionCommands = cmd.commands.filter(
                    (cmd) => cmd.type === "UPDATE_ODOO_PIVOT_DOMAIN" || cmd.type === "ADD_PIVOT"
                );
                for (const cmd of domainEditionCommands) {
                    if (!this.getters.isExistingPivot(cmd.pivotId)) {
                        continue;
                    }

                    const pivotDefinition = this.getters.getPivotDefinition(cmd.pivotId);
                    const dataSourceId = this.getPivotDataSourceId(cmd.pivotId);
                    this.dataSources.add(dataSourceId, OdooPivot, pivotDefinition);
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
                return pivotFunction.args[0]?.toString();
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
     * =ODOO.PIVOT(1,"expected_revenue","stage_id",2,"city","Brussels")
     * =ODOO.PIVOT.HEADER(1,"stage_id",2,"city","Brussels")
     * =ODOO.PIVOT.HEADER(1,"stage_id",2,"city","Brussels","measure","expected_revenue")
     *
     * the result is the same: ["stage_id", 2, "city", "Brussels"]
     *
     * If the cell is the result of ODOO.PIVOT.TABLE, the result is the domain of the cell
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
        if (functionName === "ODOO.PIVOT.TABLE") {
            const pivotId = args[0];
            const dataSource = this.getPivot(pivotId);
            if (!this.getters.isExistingPivot(pivotId) || !dataSource.isReady()) {
                return undefined;
            }
            const includeTotal = args[2];
            const includeColumnHeaders = args[3];
            const pivotCells = this.getPivotTableStructure(pivotId).getPivotCells(
                includeTotal,
                includeColumnHeaders
            );
            const pivotCol = position.col - mainPosition.col;
            const pivotRow = position.row - mainPosition.row;
            const pivotCell = pivotCells[pivotCol][pivotRow];
            const domain = pivotCell.domain;
            if (domain?.at(-2) === "measure") {
                return domain.slice(0, -2);
            }
            return domain;
        }
        const domain = args.slice(functionName === "ODOO.PIVOT" ? 2 : 1);
        if (domain.at(-2) === "measure") {
            return domain.slice(0, -2);
        }
        return domain;
    }

    /**
     * Return all possible values in the pivot for a given field.
     *
     * @param {string} pivotId Id of the pivot
     * @param {string} fieldName
     * @returns {Array<string>}
     */
    getPivotGroupByValues(pivotId, fieldName) {
        return this.getters.getPivot(pivotId).getPossibleValuesForGroupBy(fieldName);
    }

    /**
     * High level method computing the result of ODOO.PIVOT.HEADER functions.
     *
     * @param {string} pivotId Id of a pivot
     * @param {(string | number)[]} domainArgs arguments of the function (except the first one which is the pivot id)
     */
    computePivotHeaderValue(pivotId, domainArgs) {
        const dataSource = this.getters.getPivot(pivotId);
        return dataSource.computePivotHeaderValue(domainArgs);
    }

    /**
     * High level method computing the formatted result of ODOO.PIVOT.HEADER functions.
     *
     * @param {string} pivotId
     * @param {(string | number)[]} pivotArgs arguments of the function (except the first one which is the pivot id)
     */
    getPivotHeaderFormattedValue(pivotId, pivotArgs) {
        const dataSource = this.getters.getPivot(pivotId);
        const value = dataSource.computePivotHeaderValue(pivotArgs);
        if (typeof value === "string") {
            return value;
        }
        const format = this.getPivotFieldFormat(pivotId, pivotArgs.at(-2));
        const locale = this.getters.getLocale();
        return formatValue(value, { format, locale });
    }

    /**
     * @param {string} pivotId
     * @param {string} fieldName
     * @returns {string | undefined}
     */
    getPivotFieldFormat(pivotId, fieldName) {
        const dataSource = this.getPivot(pivotId);
        const { field, aggregateOperator } = dataSource.parseGroupField(fieldName);
        return this._getFieldFormat(field, aggregateOperator);
    }

    /**
     * Get the value for a pivot cell
     *
     * @param {string} pivotId Id of a pivot
     * @param {string} measure Field name of the measures
     * @param {Array<string>} domain Domain
     *
     * @returns {string|number|undefined}
     */
    getPivotCellValue(pivotId, measure, domain) {
        const dataSource = this.getters.getPivot(pivotId);
        return dataSource.getPivotCellValue(measure, domain);
    }

    getPivotTableStructure(pivotId) {
        const dataSource = this.getters.getPivot(pivotId);
        return dataSource.getTableStructure();
    }

    /**
     * @param {string} pivotId
     * @returns {OdooPivot|undefined}
     */
    getPivot(pivotId) {
        const dataSourceId = this.getPivotDataSourceId(pivotId);
        return this.dataSources.get(dataSourceId);
    }

    getPivotDataSourceId(pivotId) {
        return `pivot-${pivotId}`;
    }

    isPivotUnused(pivotId) {
        return this._getUnusedPivots().includes(pivotId);
    }

    // ---------------------------------------------------------------------
    // Private
    // ---------------------------------------------------------------------

    /**
     * @param {import("../../data_sources/metadata_repository").Field} field
     * @param {"day" | "week" | "month" | "quarter" | "year"} aggregateOperator
     * @returns {string | undefined}
     */
    _getFieldFormat(field, aggregateOperator) {
        switch (field.type) {
            case "integer":
                return "0";
            case "float":
                return "#,##0.00";
            case "monetary":
                return this.getters.getCompanyCurrencyFormat() || "#,##0.00";
            case "date":
            case "datetime": {
                const timeAdapter = pivotTimeAdapter(aggregateOperator);
                return timeAdapter.getFormat(this.getters.getLocale());
            }
            default:
                return undefined;
        }
    }

    /**
     * Refresh the cache of a pivot
     *
     * @param {string} pivotId Id of the pivot
     */
    _refreshOdooPivot(pivotId) {
        const dataSource = this.getters.getPivot(pivotId);
        dataSource.load({ reload: true });
    }

    /**
     * Refresh the cache of all the pivots
     */
    _refreshOdooPivots() {
        for (const pivotId of this.getters.getPivotIds()) {
            this._refreshOdooPivot(pivotId, false);
        }
    }

    /**
     * @param {string} pisvotId
     */
    _setupPivotDataSource(pivotId) {
        const dataSourceId = this.getPivotDataSourceId(pivotId);
        const definition = this.getters.getPivotDefinition(pivotId);
        if (!this.dataSources.contains(dataSourceId)) {
            this.dataSources.add(dataSourceId, OdooPivot, definition);
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
