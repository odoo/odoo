/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { getFirstListFunction } from "../list_helpers";
import { Domain } from "@web/core/domain";
import { ListDataSource } from "../list_data_source";
import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
import { OdooUIPlugin } from "@spreadsheet/plugins";

const { astToFormula, constants } = spreadsheet;
const { isEvaluationError } = spreadsheet.helpers;
const { PIVOT_TABLE_CONFIG } = constants;

/**
 * @typedef {import("./list_core_plugin").SpreadsheetList} SpreadsheetList
 */

export class ListUIPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ ([
        "getListComputedDomain",
        "getListHeaderValue",
        "getListIdFromPosition",
        "getListCellValueAndFormat",
        "getListDataSource",
        "getAsyncListDataSource",
        "isListUnused",
    ]);
    constructor(config) {
        super(config);
        /** @type {string} */
        this.env = config.custom.env;

        /** @type {Record<string, ListDataSource>} */
        this.lists = {};

        this.custom = config.custom;

        globalFiltersFieldMatchers["list"] = {
            ...globalFiltersFieldMatchers["list"],
            getFields: (listId) => this.getListDataSource(listId).getFields(),
            waitForReady: () => this.getListsWaitForReady(),
        };
    }

    beforeHandle(cmd) {
        switch (cmd.type) {
            case "START":
                for (const listId of this.getters.getListIds()) {
                    this._setupListDataSource(listId, 0);
                }

                // make sure the domains are correctly set before
                // any evaluation
                this._addDomains();
                break;
        }
    }

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "INSERT_ODOO_LIST": {
                const { id, linesNumber } = cmd;
                this._setupListDataSource(id, linesNumber);
                break;
            }
            case "INSERT_ODOO_LIST_WITH_TABLE": {
                this.dispatch("INSERT_ODOO_LIST", cmd);
                this._addTable(cmd);
                break;
            }
            case "RE_INSERT_ODOO_LIST_WITH_TABLE": {
                this.dispatch("RE_INSERT_ODOO_LIST", cmd);
                this._addTable(cmd);
                break;
            }
            case "DUPLICATE_ODOO_LIST": {
                this._setupListDataSource(cmd.newListId, 0);
                break;
            }
            case "REFRESH_ALL_DATA_SOURCES":
                this._refreshOdooLists();
                break;
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
            case "REMOVE_GLOBAL_FILTER":
            case "SET_GLOBAL_FILTER_VALUE":
            case "CLEAR_GLOBAL_FILTER_VALUE":
                this._addDomains();
                break;
            case "UPDATE_ODOO_LIST":
            case "UPDATE_ODOO_LIST_DOMAIN": {
                const listDefinition = this.getters.getListModelDefinition(cmd.listId);
                const dataSourceId = this._getListDataSourceId(cmd.listId);
                this.lists[dataSourceId] = new ListDataSource(this.custom, listDefinition);
                break;
            }
            case "DELETE_SHEET":
                this.unusedLists = undefined;
                break;
            case "UPDATE_CELL":
                this.unusedLists = undefined;
                break;
            case "UNDO":
            case "REDO": {
                this.unusedLists = undefined;
                if (
                    cmd.commands.find((command) =>
                        [
                            "ADD_GLOBAL_FILTER",
                            "EDIT_GLOBAL_FILTER",
                            "REMOVE_GLOBAL_FILTER",
                        ].includes(command.type)
                    )
                ) {
                    this._addDomains();
                }

                const updateCommands = cmd.commands.filter(
                    (cmd) =>
                        cmd.type === "UPDATE_ODOO_LIST_DOMAIN" ||
                        cmd.type === "UPDATE_ODOO_LIST" ||
                        cmd.type === "INSERT_ODOO_LIST"
                );
                for (const cmd of updateCommands) {
                    if (!this.getters.isExistingList(cmd.listId)) {
                        continue;
                    }

                    const listDefinition = this.getters.getListModelDefinition(cmd.listId);
                    const dataSourceId = this._getListDataSourceId(cmd.listId);
                    this.lists[dataSourceId] = new ListDataSource(this.custom, listDefinition);
                }
                break;
            }
        }
    }

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    _setupListDataSource(listId, limit, definition) {
        const dataSourceId = this._getListDataSourceId(listId);
        definition = definition || this.getters.getListModelDefinition(listId);
        if (!(dataSourceId in this.lists)) {
            this.lists[dataSourceId] = new ListDataSource(this.custom, { ...definition, limit });
        }
    }

    /**
     * Add an additional domain to a list
     *
     * @private
     *
     * @param {string} listId list id
     *
     */
    _addDomain(listId) {
        const domainList = [];
        for (const [filterId, fieldMatch] of Object.entries(
            this.getters.getListFieldMatch(listId)
        )) {
            domainList.push(this.getters.getGlobalFilterDomain(filterId, fieldMatch));
        }
        const domain = Domain.combine(domainList, "AND").toString();
        this.getters.getListDataSource(listId).addDomain(domain);
    }

    /**
     * Add an additional domain to all lists
     *
     * @private
     *
     */
    _addDomains() {
        for (const listId of this.getters.getListIds()) {
            this._addDomain(listId);
        }
    }

    /**
     * Refresh the cache of a list
     * @param {string} listId Id of the list
     */
    _refreshOdooList(listId) {
        this.getters.getListDataSource(listId).load({ reload: true });
    }

    /**
     * Refresh the cache of all the lists
     */
    _refreshOdooLists() {
        for (const listId of this.getters.getListIds()) {
            this._refreshOdooList(listId);
        }
    }

    _getListDataSourceId(listId) {
        return `list-${listId}`;
    }

    _getUnusedLists() {
        if (this.unusedLists !== undefined) {
            return this.unusedLists;
        }
        const unusedLists = new Set(this.getters.getListIds());
        for (const sheetId of this.getters.getSheetIds()) {
            for (const cellId in this.getters.getCells(sheetId)) {
                const position = this.getters.getCellPosition(cellId);
                const listId = this.getListIdFromPosition(position);
                if (listId) {
                    unusedLists.delete(listId);
                    if (!unusedLists.size) {
                        this.unusedLists = [];
                        return this.unusedLists;
                    }
                }
            }
        }
        this.unusedLists = [...unusedLists];
        return this.unusedLists;
    }

    _getListFormat(listId, position, field) {
        const locale = this.getters.getLocale();
        switch (field?.type) {
            case "integer":
                return "0";
            case "float":
                return "#,##0.00";
            case "monetary": {
                const currency = this.getListCurrency(listId, position, field.currency_field);
                if (!currency) {
                    return "#,##0.00";
                }
                return this.getters.computeFormatFromCurrency(currency);
            }
            case "date":
                return locale.dateFormat;
            case "datetime":
                return locale.dateFormat + " " + locale.timeFormat;
            case "char":
            case "text":
                return "@";
            default:
                return undefined;
        }
    }

    _addTable({ sheetId, col, row, linesNumber, columns }) {
        const zone = {
            left: col,
            right: col + columns.length - 1,
            top: row,
            bottom: row + linesNumber,
        };
        this.dispatch("CREATE_TABLE", {
            tableType: "static",
            sheetId,
            ranges: [this.getters.getRangeDataFromZone(sheetId, zone)],
            config: { ...PIVOT_TABLE_CONFIG, firstColumn: false },
        });
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /**
     * Get the computed domain of a list
     *
     * @param {string} listId Id of the list
     * @returns {Array}
     */
    getListComputedDomain(listId) {
        return this.getters.getListDataSource(listId).getComputedDomain();
    }

    /**
     * Get the id of the list at the given position. Returns undefined if there
     * is no list at this position
     *
     * @param {{ sheetId: string; col: number; row: number}} position
     *
     * @returns {string|undefined}
     */
    getListIdFromPosition(position) {
        const cell = this.getters.getCorrespondingFormulaCell(position);
        const sheetId = position.sheetId;
        if (cell && cell.isFormula) {
            const listFunction = getFirstListFunction(cell.compiledFormula.tokens);
            if (listFunction) {
                const content = astToFormula(listFunction.args[0]);
                return this.getters.evaluateFormula(sheetId, content)?.toString();
            }
        }
        return undefined;
    }

    /**
     * Get the value of a list header
     *
     * @param {string} listId Id of a list
     * @param {string} fieldName
     */
    getListHeaderValue(listId, fieldName) {
        return this.getters.getListDataSource(listId).getListHeaderValue(fieldName);
    }

    /**
     * Get the value for a field of a record in the list
     * @param {string} listId Id of the list
     * @param {number} position Position of the record in the list
     * @param {string} fieldName Field Name
     *
     * @returns {string|undefined}
     */
    getListCellValueAndFormat(listId, position, fieldName) {
        const dataSource = this.getters.getListDataSource(listId);
        dataSource.addFieldToFetch(fieldName);
        const value = dataSource.getListCellValue(position, fieldName);
        if (typeof value === "object" && isEvaluationError(value.value)) {
            return value;
        }
        const field = dataSource.getField(fieldName);
        const format = this._getListFormat(listId, position, field);
        return { value, format };
    }

    getListCurrency(listId, position, fieldName) {
        return this.getters.getListDataSource(listId).getListCurrency(position, fieldName);
    }

    /**
     * @param {string} id
     * @returns {import("@spreadsheet/list/list_data_source").default|undefined}
     */
    getListDataSource(id) {
        const dataSourceId = this._getListDataSourceId(id);
        return this.lists[dataSourceId];
    }

    /**
     * @param {string} id
     * @returns {Promise<import("@spreadsheet/list/list_data_source").ListDataSource>}
     */
    async getAsyncListDataSource(id) {
        const dataSource = this.getListDataSource(id);
        await dataSource.load();
        return dataSource;
    }

    /**
     *
     * @return {Promise[]}
     */
    getListsWaitForReady() {
        return this.getters
            .getListIds()
            .map((listId) => this.getListDataSource(listId).loadMetadata());
    }

    isListUnused(listId) {
        return this._getUnusedLists().includes(listId);
    }
}
