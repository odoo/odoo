/** @odoo-module */
//@ts-check
/**
 *
 * @typedef {import("@spreadsheet").PivotDefinition} PivotDefinition
 * @typedef {import("@spreadsheet").PivotRuntime} PivotRuntime
 * @typedef {import("@spreadsheet").AllCoreCommand} AllCoreCommand
 *
 * @typedef {Object} LocalPivot
 * @property {string} id
 * @property {PivotDefinition} definition
 * @property {Record<string, FieldMatching>} fieldMatching
 *
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").FieldMatching} FieldMatching
 * @typedef {import("../pivot_table.js").PivotCell} PivotCell
 */

import { helpers } from "@odoo/o-spreadsheet";
import { makePivotFormula } from "../pivot_helpers";
import { getMaxObjectId } from "@spreadsheet/helpers/helpers";
import { SpreadsheetPivotTable } from "../pivot_table";
import { CommandResult } from "../../o_spreadsheet/cancelled_reason";
import { _t } from "@web/core/l10n/translation";
import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
import { sprintf } from "@web/core/utils/strings";
import { checkFilterFieldMatching } from "@spreadsheet/global_filters/helpers";
import { Domain } from "@web/core/domain";
import { deepCopy } from "@web/core/utils/objects";
import { OdooCorePlugin } from "@spreadsheet/plugins";

const { isDefined } = helpers;

export class PivotCorePlugin extends OdooCorePlugin {
    static getters = /** @type {const} */ ([
        "getNextPivotId",
        "getPivotDefinition",
        "getPivotDisplayName",
        "getPivotIds",
        "getPivotName",
        "isExistingPivot",
        "getPivotFieldMatch",
        "getPivotFieldMatching",
    ]);
    constructor(config) {
        super(config);

        this.nextId = 1;
        /** @type {Object.<string, LocalPivot>} */
        this.pivots = {};
        globalFiltersFieldMatchers["pivot"] = {
            getIds: () => this.getters.getPivotIds(),
            getDisplayName: (pivotId) => this.getters.getPivotName(pivotId),
            getTag: (pivotId) => sprintf(_t("Pivot #%s"), pivotId),
            getFieldMatching: (pivotId, filterId) => this.getPivotFieldMatching(pivotId, filterId),
            getModel: (pivotId) => this.getPivotDefinition(pivotId).model,
        };
    }

    /**
     * @param {AllCoreCommand} cmd
     *
     * @returns {string | string[]}
     */
    allowDispatch(cmd) {
        switch (cmd.type) {
            case "RENAME_ODOO_PIVOT":
                if (!(cmd.pivotId in this.pivots)) {
                    return CommandResult.PivotIdNotFound;
                }
                if (cmd.name === "") {
                    return CommandResult.EmptyName;
                }
                break;
            case "INSERT_PIVOT":
                if (cmd.id !== this.nextId.toString()) {
                    return CommandResult.InvalidNextId;
                }
                break;
            case "DUPLICATE_PIVOT":
                if (!(cmd.pivotId in this.pivots)) {
                    return CommandResult.PivotIdNotFound;
                }
                if (cmd.newPivotId !== this.nextId.toString()) {
                    return CommandResult.InvalidNextId;
                }
                break;
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
                if (cmd.pivot) {
                    return checkFilterFieldMatching(cmd.pivot);
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
            case "INSERT_PIVOT": {
                const { sheetId, col, row, id, definition } = cmd;
                /** @type { { col: number, row: number } } */
                const position = { col, row };
                const { cols, rows, measures, rowTitle } = cmd.table;
                const table = new SpreadsheetPivotTable(cols, rows, measures, rowTitle);
                const def = this._convertPivotDefinition(definition);
                this._addPivot(id, def);
                this._insertPivot(sheetId, position, id, table);
                this.history.update("nextId", parseInt(id, 10) + 1);
                break;
            }
            case "RE_INSERT_PIVOT": {
                const { sheetId, col, row, id } = cmd;
                /** @type { { col: number, row: number } } */
                const position = { col, row };
                const { cols, rows, measures, rowTitle } = cmd.table;
                const table = new SpreadsheetPivotTable(cols, rows, measures, rowTitle);
                this._insertPivot(sheetId, position, id, table);
                break;
            }
            case "RENAME_ODOO_PIVOT": {
                this.history.update("pivots", cmd.pivotId, "definition", "name", cmd.name);
                break;
            }
            case "REMOVE_PIVOT": {
                const pivots = { ...this.pivots };
                delete pivots[cmd.pivotId];
                this.history.update("pivots", pivots);
                break;
            }
            case "DUPLICATE_PIVOT": {
                const { pivotId, newPivotId } = cmd;
                const definition = deepCopy(this.pivots[pivotId].definition);
                this._addPivot(newPivotId, definition);
                this.history.update("nextId", parseInt(newPivotId, 10) + 1);
                break;
            }
            case "UPDATE_ODOO_PIVOT_DOMAIN": {
                this.history.update("pivots", cmd.pivotId, "definition", "domain", cmd.domain);
                break;
            }
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
                if (cmd.pivot) {
                    this._setPivotFieldMatching(cmd.filter.id, cmd.pivot);
                }
                break;
            case "REMOVE_GLOBAL_FILTER":
                this._onFilterDeletion(cmd.id);
                break;
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
        return `(#${id}) ${this.getPivotName(id)}`;
    }

    /**
     * @param {string} id
     * @returns {string}
     */
    getPivotName(id) {
        return _t(this.pivots[id].definition.name);
    }

    /**
     * @param {string} id
     * @returns {Record<string, FieldMatching>}
     */
    getPivotFieldMatch(id) {
        return this.pivots[id].fieldMatching;
    }

    /**
     * Retrieve the next available id for a new pivot
     *
     * @returns {string} id
     */
    getNextPivotId() {
        return this.nextId.toString();
    }

    /**
     * @param {string} id Id of the pivot
     *
     * @returns {PivotDefinition}
     */
    getPivotDefinition(id) {
        return deepCopy(this.pivots[id].definition);
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
     * @param {number} pivotId Id of the pivot
     *
     * @returns {boolean}
     */
    isExistingPivot(pivotId) {
        return pivotId in this.pivots;
    }

    /**
     * Get the current pivotFieldMatching on a pivot
     *
     * @param {string} pivotId
     * @param {string} filterId
     */
    getPivotFieldMatching(pivotId, filterId) {
        return this.pivots[pivotId].fieldMatching[filterId];
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Sets the current pivotFieldMatching on a pivot
     *
     * @param {string} filterId
     * @param {Record<string,FieldMatching>} pivotFieldMatches
     */
    _setPivotFieldMatching(filterId, pivotFieldMatches) {
        const pivots = { ...this.pivots };
        for (const [pivotId, fieldMatch] of Object.entries(pivotFieldMatches)) {
            pivots[pivotId].fieldMatching[filterId] = fieldMatch;
        }
        this.history.update("pivots", pivots);
    }

    _onFilterDeletion(filterId) {
        const pivots = { ...this.pivots };
        for (const pivotId in pivots) {
            this.history.update("pivots", pivotId, "fieldMatching", filterId, undefined);
        }
    }

    /**
     * @param {PivotRuntime} runtimeDefinition
     *
     * @returns {PivotDefinition}
     */
    _convertPivotDefinition(runtimeDefinition) {
        return {
            colGroupBys: runtimeDefinition.metaData.colGroupBys,
            rowGroupBys: runtimeDefinition.metaData.rowGroupBys,
            measures: runtimeDefinition.metaData.activeMeasures,
            model: runtimeDefinition.metaData.resModel,
            domain: runtimeDefinition.searchParams.domain,
            context: runtimeDefinition.searchParams.context,
            name: runtimeDefinition.name,
            sortedColumn: runtimeDefinition.metaData.sortedColumn || null,
        };
    }

    /**
     * @param {string} id
     * @param {PivotDefinition} definition
     * @param {Record<string, FieldMatching>} [fieldMatching]
     */
    _addPivot(id, definition, fieldMatching = undefined) {
        const pivots = { ...this.pivots };
        if (!fieldMatching) {
            const model = definition.model;
            fieldMatching = this.getters.getFieldMatchingForModel(model);
        }
        pivots[id] = {
            id,
            definition,
            fieldMatching,
        };
        this.history.update("pivots", pivots);
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
     * @param {PivotCell} pivotCell
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
                /** @type {PivotDefinition} */
                const definition = deepCopy(pivot);
                definition.measures = pivot.measures.map((elt) => elt.field);
                this._addPivot(id, definition, pivot.fieldMatching);
            }
        }
        this.nextId = data.pivotNextId || getMaxObjectId(this.pivots) + 1;
    }
    /**
     * Export the pivots
     *
     * @param {Object} data
     */
    export(data) {
        data.pivots = {};
        for (const id in this.pivots) {
            data.pivots[id] = deepCopy(this.getPivotDefinition(id));
            data.pivots[id].measures = data.pivots[id].measures.map((elt) => ({ field: elt }));
            data.pivots[id].fieldMatching = this.pivots[id].fieldMatching;
            data.pivots[id].domain = new Domain(data.pivots[id].domain).toJson();
        }
        data.pivotNextId = this.nextId;
    }
}
