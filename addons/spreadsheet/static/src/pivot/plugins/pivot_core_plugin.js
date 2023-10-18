/** @odoo-module */

/**
 *
 * @typedef {Object} PivotDefinition
 * @property {Array<string>} colGroupBys
 * @property {Array<string>} rowGroupBys
 * @property {Array<string>} measures
 * @property {string} model
 * @property {Array} domain
 * @property {Object} context
 * @property {string} name
 * @property {string} id
 * @property {Object | null} sortedColumn
 *
 * @typedef {Object} Pivot
 * @property {string} id
 * @property {string} dataSourceId
 * @property {PivotDefinition} definition
 * @property {Object} fieldMatching
 *
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").FieldMatching} FieldMatching
 * @typedef {import("../pivot_table.js").PivotCell} PivotCell
 */

import { CorePlugin, helpers } from "@odoo/o-spreadsheet";
import { makePivotFormula } from "../pivot_helpers";
import { getMaxObjectId } from "@spreadsheet/helpers/helpers";
import { SpreadsheetPivotTable } from "../pivot_table";
import { CommandResult } from "../../o_spreadsheet/cancelled_reason";
import { _t } from "@web/core/l10n/translation";
import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
import { sprintf } from "@web/core/utils/strings";
import { checkFilterFieldMatching } from "@spreadsheet/global_filters/helpers";
import { Domain } from "@web/core/domain";

const { isDefined } = helpers;

export class PivotCorePlugin extends CorePlugin {
    constructor(config) {
        super(config);

        this.nextId = 1;
        /** @type {Object.<string, Pivot>} */
        this.pivots = {};
        globalFiltersFieldMatchers["pivot"] = {
            getIds: () => this.getters.getPivotIds(),
            getDisplayName: (pivotId) => this.getters.getPivotName(pivotId),
            getTag: (pivotId) => sprintf(_t("Pivot #%s"), pivotId),
            getFieldMatching: (pivotId, filterId) => this.getPivotFieldMatching(pivotId, filterId),
            getModel: (pivotId) => this.getPivotDefinition(pivotId).model,
        };
    }

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
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
                if (cmd.pivot) {
                    return checkFilterFieldMatching(cmd.pivot);
                }
        }
        return CommandResult.Success;
    }

    /**
     * Handle a spreadsheet command
     *
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "INSERT_PIVOT": {
                const { sheetId, col, row, id, definition } = cmd;
                /** @type { col: number, row: number } */
                const position = { col, row };
                const { cols, rows, measures, rowTitle } = cmd.table;
                const table = new SpreadsheetPivotTable(cols, rows, measures, rowTitle);
                this._addPivot(id, definition);
                this._insertPivot(sheetId, position, id, table);
                this.history.update("nextId", parseInt(id, 10) + 1);
                break;
            }
            case "RE_INSERT_PIVOT": {
                const { sheetId, col, row, id } = cmd;
                /** @type { col: number, row: number } */
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
            case "UPDATE_ODOO_PIVOT_DOMAIN": {
                this.history.update(
                    "pivots",
                    cmd.pivotId,
                    "definition",
                    "searchParams",
                    "domain",
                    cmd.domain
                );
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
     * @returns {string}
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
        const def = this.pivots[id].definition;
        return {
            colGroupBys: [...def.metaData.colGroupBys],
            context: { ...def.searchParams.context },
            domain: def.searchParams.domain,
            id,
            measures: [...def.metaData.activeMeasures],
            model: def.metaData.resModel,
            rowGroupBys: [...def.metaData.rowGroupBys],
            name: def.name,
            sortedColumn: def.metaData.sortedColumn ? { ...def.metaData.sortedColumn } : null,
        };
    }

    getPivotModelDefinition(id) {
        return this.pivots[id].definition;
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
     * @param {string} id
     * @param {PivotDefinition} definition
     * @param {string} dataSourceId
     */
    _addPivot(id, definition, fieldMatching = undefined) {
        const pivots = { ...this.pivots };
        if (!fieldMatching) {
            const model = definition.metaData.resModel;
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
        const pivotCells = table.pivotCells;
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
     * @param {{ col: number, row: number }} position
     * @param {string} pivotId
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
                const definition = {
                    metaData: {
                        colGroupBys: pivot.colGroupBys,
                        rowGroupBys: pivot.rowGroupBys,
                        activeMeasures: pivot.measures.map((elt) => elt.field),
                        resModel: pivot.model,
                        sortedColumn: !pivot.sortedColumn
                            ? undefined
                            : {
                                  groupId: pivot.sortedColumn.groupId,
                                  measure: pivot.sortedColumn.measure,
                                  order: pivot.sortedColumn.order,
                              },
                    },
                    searchParams: {
                        groupBy: [],
                        orderBy: [],
                        domain: pivot.domain,
                        context: pivot.context,
                    },
                    name: pivot.name,
                };
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
            data.pivots[id] = JSON.parse(JSON.stringify(this.getPivotDefinition(id)));
            data.pivots[id].measures = data.pivots[id].measures.map((elt) => ({ field: elt }));
            data.pivots[id].fieldMatching = this.pivots[id].fieldMatching;
            data.pivots[id].domain = new Domain(data.pivots[id].domain).toJson();
        }
        data.pivotNextId = this.nextId;
    }
}

PivotCorePlugin.getters = [
    "getNextPivotId",
    "getPivotDefinition",
    "getPivotDisplayName",
    "getPivotIds",
    "getPivotName",
    "isExistingPivot",
    "getPivotFieldMatch",
    "getPivotFieldMatching",
    "getPivotModelDefinition",
];
