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
 */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { makePivotFormula } from "../pivot_helpers";
import { getMaxObjectId } from "@spreadsheet/helpers/helpers";
import { HEADER_STYLE, TOP_LEVEL_STYLE, MEASURE_STYLE } from "@spreadsheet/helpers/constants";
import PivotDataSource from "../pivot_data_source";
import { SpreadsheetPivotTable } from "../pivot_table";
import CommandResult from "../../o_spreadsheet/cancelled_reason";
import { _t } from "@web/core/l10n/translation";
import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
import { sprintf } from "@web/core/utils/strings";

const { CorePlugin } = spreadsheet;

export default class PivotCorePlugin extends CorePlugin {
    constructor(getters, history, range, dispatch, config, uuidGenerator) {
        super(getters, history, range, dispatch, config, uuidGenerator);
        this.dataSources = config.dataSources;

        this.nextId = 1;
        /** @type {Object.<string, Pivot>} */
        this.pivots = {};
        globalFiltersFieldMatchers["pivot"] = {
            geIds: () => this.getters.getPivotIds(),
            getDisplayName: (pivotId) => this.getters.getPivotName(pivotId),
            getTag: (pivotId) => sprintf(_t("Pivot #%s"), pivotId),
            getFieldMatching: (pivotId, filterId) => this.getPivotFieldMatching(pivotId, filterId),
            waitForReady: () => this.getPivotsWaitForReady(),
            getModel: (pivotId) => this.getPivotDefinition(pivotId).model,
            getFields: (pivotId) => this.getPivotDataSource(pivotId).getFields(),
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
                const { sheetId, col, row, id, definition, dataSourceId } = cmd;
                /** @type [number,number] */
                const anchor = [col, row];
                const { cols, rows, measures } = cmd.table;
                const table = new SpreadsheetPivotTable(cols, rows, measures);
                this._addPivot(id, definition, dataSourceId);
                this._insertPivot(sheetId, anchor, id, table);
                this.nextId = parseInt(id, 10) + 1;
                break;
            }
            case "RE_INSERT_PIVOT": {
                const { sheetId, col, row, id } = cmd;
                /** @type [number,number] */
                const anchor = [col, row];
                const { cols, rows, measures } = cmd.table;
                const table = new SpreadsheetPivotTable(cols, rows, measures);
                this._insertPivot(sheetId, anchor, id, table);
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
                const pivot = this.pivots[cmd.pivotId];
                this.dataSources.add(pivot.dataSourceId, PivotDataSource, pivot.definition);
                break;
            }
            case "UNDO":
            case "REDO": {
                const domainEditionCommands = cmd.commands.filter(
                    (cmd) => cmd.type === "UPDATE_ODOO_PIVOT_DOMAIN"
                );
                for (const cmd of domainEditionCommands) {
                    const pivot = this.pivots[cmd.pivotId];
                    this.dataSources.add(pivot.dataSourceId, PivotDataSource, pivot.definition);
                }
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
     * @returns {PivotDataSource|undefined}
     */
    getPivotDataSource(id) {
        const dataSourceId = this.pivots[id].dataSourceId;
        return this.dataSources.get(dataSourceId);
    }

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
     * @param {string} id
     * @returns {Promise<PivotDataSource>}
     */
    async getAsyncPivotDataSource(id) {
        const dataSourceId = this.pivots[id].dataSourceId;
        await this.dataSources.load(dataSourceId);
        return this.getPivotDataSource(id);
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
            domain: [...def.searchParams.domain],
            id,
            measures: [...def.metaData.activeMeasures],
            model: def.metaData.resModel,
            rowGroupBys: [...def.metaData.rowGroupBys],
            name: def.name,
            sortedColumn: def.metaData.sortedColumn ? { ...def.metaData.sortedColumn } : null,
        };
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
     *
     * @return {Promise[]}
     */
    getPivotsWaitForReady() {
        return this.getPivotIds().map((pivotId) => this.getPivotDataSource(pivotId).loadMetadata());
    }

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
    _addPivot(id, definition, dataSourceId, fieldMatching = {}) {
        const pivots = { ...this.pivots };
        pivots[id] = {
            id,
            definition,
            dataSourceId,
            fieldMatching,
        };

        if (!this.dataSources.contains(dataSourceId)) {
            this.dataSources.add(dataSourceId, PivotDataSource, definition);
        }
        this.history.update("pivots", pivots);
    }

    /**
     * @param {string} sheetId
     * @param {[number, number]} anchor
     * @param {string} id
     * @param {SpreadsheetPivotTable} table
     */
    _insertPivot(sheetId, anchor, id, table) {
        this._resizeSheet(sheetId, anchor, table);
        this._insertColumns(sheetId, anchor, id, table);
        this._insertRows(sheetId, anchor, id, table);
        this._insertBody(sheetId, anchor, id, table);
    }

    /**
     * @param {string} sheetId
     * @param {[number, number]} anchor
     * @param {string} id
     * @param {SpreadsheetPivotTable} table
     */
    _insertColumns(sheetId, anchor, id, table) {
        let anchorLeft = anchor[0] + 1;
        let anchorTop = anchor[1];
        for (const _row of table.getColHeaders()) {
            anchorLeft = anchor[0] + 1;
            for (const cell of _row) {
                const args = [id];
                for (let i = 0; i < cell.fields.length; i++) {
                    args.push(cell.fields[i]);
                    args.push(cell.values[i]);
                }
                if (cell.width > 1) {
                    this._merge(sheetId, {
                        top: anchorTop,
                        bottom: anchorTop,
                        left: anchorLeft,
                        right: anchorLeft + cell.width - 1,
                    });
                }
                this._addPivotFormula(sheetId, anchorLeft, anchorTop, "ODOO.PIVOT.HEADER", args);
                anchorLeft += cell.width;
            }
            anchorTop++;
        }
        const colHeight = table.getColHeight();
        const colWidth = table.getColWidth();
        const lastRowBeforeMeasureRow = anchor[1] + colHeight - 2;
        const right = anchor[0] + colWidth;
        const left = right - table.getNumberOfMeasures() + 1;
        for (let anchorTop = anchor[1]; anchorTop < lastRowBeforeMeasureRow; anchorTop++) {
            this._merge(sheetId, { top: anchorTop, bottom: anchorTop, left, right });
        }
        const headersZone = {
            top: anchor[1],
            bottom: lastRowBeforeMeasureRow,
            left: anchor[0],
            right: anchor[0] + colWidth,
        };
        const measuresZone = {
            top: anchor[1] + colHeight - 1,
            bottom: anchor[1] + colHeight - 1,
            left: anchor[0],
            right: anchor[0] + colWidth,
        };
        this.dispatch("SET_FORMATTING", { sheetId, target: [headersZone], style: TOP_LEVEL_STYLE });
        this.dispatch("SET_FORMATTING", { sheetId, target: [measuresZone], style: MEASURE_STYLE });
    }

    /**
     * Merge a zone
     *
     * @param {string} sheetId
     * @param {Object} zone
     *
     * @private
     */
    _merge(sheetId, zone) {
        this.dispatch("ADD_MERGE", { sheetId, target: [zone] });
    }

    /**
     * @param {string} sheetId
     * @param {[number,number]} anchor
     * @param {SpreadsheetPivotTable} table
     */
    _resizeSheet(sheetId, anchor, table) {
        const colLimit = table.getColWidth() + 1; // +1 for the Top-Left
        const numberCols = this.getters.getNumberCols(sheetId);
        const deltaCol = numberCols - anchor[0];
        if (deltaCol < colLimit) {
            this.dispatch("ADD_COLUMNS_ROWS", {
                dimension: "COL",
                base: numberCols - 1,
                sheetId: sheetId,
                quantity: colLimit - deltaCol,
                position: "after",
            });
        }
        const rowLimit = table.getColHeight() + table.getRowHeight();
        const numberRows = this.getters.getNumberRows(sheetId);
        const deltaRow = numberRows - anchor[1];
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
     * @param {[number, number]} anchor
     * @param {string} id
     * @param {SpreadsheetPivotTable} table
     */
    _insertRows(sheetId, anchor, id, table) {
        let y = anchor[1] + table.getColHeight();
        const x = anchor[0];
        for (const row of table.getRowHeaders()) {
            const args = [id];
            for (let i = 0; i < row.fields.length; i++) {
                args.push(row.fields[i]);
                args.push(row.values[i]);
            }
            this._addPivotFormula(sheetId, x, y, "ODOO.PIVOT.HEADER", args);
            if (row.indent <= 2) {
                const target = [{ top: y, bottom: y, left: x, right: x }];
                const style = row.indent === 2 ? HEADER_STYLE : TOP_LEVEL_STYLE;
                this.dispatch("SET_FORMATTING", { sheetId, target, style });
            }
            y++;
        }
    }

    /**
     * @param {string} sheetId
     * @param {[number, number]} anchor
     * @param {string} id
     * @param {SpreadsheetPivotTable} table
     */
    _insertBody(sheetId, anchor, id, table) {
        let x = anchor[0] + 1;
        for (const col of table.getMeasureHeaders()) {
            let y = anchor[1] + table.getColHeight();
            const measure = col.values[col.values.length - 1];
            for (const row of table.getRowHeaders()) {
                const args = [id, measure];
                for (let i = 0; i < row.fields.length; i++) {
                    args.push(row.fields[i]);
                    args.push(row.values[i]);
                }
                for (let i = 0; i < col.fields.length - 1; i++) {
                    args.push(col.fields[i]);
                    args.push(col.values[i]);
                }
                this._addPivotFormula(sheetId, x, y, "ODOO.PIVOT", args);
                y++;
            }
            x++;
        }
    }

    /**
     * @param {string} sheetId
     * @param {number} col
     * @param {number} row
     * @param {string} formula
     * @param {Array<string>} args
     */
    _addPivotFormula(sheetId, col, row, formula, args) {
        this.dispatch("UPDATE_CELL", {
            sheetId,
            col,
            row,
            content: makePivotFormula(formula, args),
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
                this._addPivot(id, definition, this.uuidGenerator.uuidv4(), pivot.fieldMatching);
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
    "getAsyncPivotDataSource",
    "isExistingPivot",
    "getPivotDataSource",
    "getPivotFieldMatch",
    "getPivotFieldMatching",
];
