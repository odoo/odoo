/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { getFirstListFunction, getNumberOfListFormulas } from "../list_helpers";
import { Domain } from "@web/core/domain";
import { ListDataSource } from "../list_data_source";
import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";

const { astToFormula } = spreadsheet;

/**
 * @typedef {import("./list_core_plugin").SpreadsheetList} SpreadsheetList
 */

export class ListUIPlugin extends spreadsheet.UIPlugin {
    constructor(config) {
        super(config);
        /** @type {string} */
        this.selectedListId = undefined;
        this.env = config.custom.env;

        this.dataSources = config.custom.dataSources;

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
            case "START":
                for (const sheetId of this.getters.getSheetIds()) {
                    const cells = this.getters.getCells(sheetId);
                    for (const cell of Object.values(cells)) {
                        if (cell.isFormula) {
                            this._addListPositionToDataSource(cell);
                        }
                    }
                }
                break;
            case "INSERT_ODOO_LIST": {
                const { id, linesNumber } = cmd;
                this._setupListDataSource(id, linesNumber);
                break;
            }
            case "SELECT_ODOO_LIST":
                this._selectList(cmd.listId);
                break;
            case "REMOVE_ODOO_LIST":
                if (cmd.listId === this.selectedListId) {
                    this.selectedListId = undefined;
                }
                break;
            case "REFRESH_ODOO_LIST":
                this._refreshOdooList(cmd.listId);
                break;
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
            case "UPDATE_ODOO_LIST_DOMAIN": {
                const listDefinition = this.getters.getListModelDefinition(cmd.listId);
                const dataSourceId = this._getListDataSourceId(cmd.listId);
                this.dataSources.add(dataSourceId, ListDataSource, listDefinition);
                break;
            }
            case "UPDATE_CELL":
                if (cmd.content) {
                    const position = { sheetId: cmd.sheetId, col: cmd.col, row: cmd.row };
                    const cell = this.getters.getCell(position);
                    if (cell && cell.isFormula) {
                        this._addListPositionToDataSource(cell);
                    }
                }
                break;
            case "UNDO":
            case "REDO": {
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

                const domainEditionCommands = cmd.commands.filter(
                    (cmd) =>
                        cmd.type === "UPDATE_ODOO_LIST_DOMAIN" || cmd.type === "INSERT_ODOO_LIST"
                );
                for (const cmd of domainEditionCommands) {
                    if (!this.getters.isExistingList(cmd.listId)) {
                        continue;
                    }

                    const listDefinition = this.getters.getListModelDefinition(cmd.listId);
                    const dataSourceId = this._getListDataSourceId(cmd.listId);
                    this.dataSources.add(dataSourceId, ListDataSource, listDefinition);
                }

                if (!this.getters.getListIds().length) {
                    this.selectedListId = undefined;
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
        if (!this.dataSources.contains(dataSourceId)) {
            this.dataSources.add(dataSourceId, ListDataSource, {
                ...definition,
                limit,
            });
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

    /**
     * Select the given list id. If the id is undefined, it unselect the list.
     * @param {number|undefined} listId Id of the list, or undefined to remove
     *                                  the selected list
     */
    _selectList(listId) {
        this.selectedListId = listId;
    }

    _getListDataSourceId(listId) {
        return `list-${listId}`;
    }

    /**
     * Extract the position of the records asked in the given formula and
     * increase the max position of the corresponding data source.
     *
     * @param {string} content Odoo list formula
     */
    _addListPositionToDataSource(cell) {
        if (getNumberOfListFormulas(cell.compiledFormula.tokens) !== 1) {
            return;
        }
        const { functionName, args } = getFirstListFunction(cell.compiledFormula.tokens);
        if (functionName !== "ODOO.LIST") {
            return;
        }
        const [listId, positionArg] = args.map((arg) => arg.value.toString());

        if (!this.getters.getListIds().includes(listId)) {
            return;
        }
        const position = parseInt(positionArg, 10);
        if (isNaN(position)) {
            return;
        }
        const dataSourceId = this._getListDataSourceId(listId);
        if (!this.dataSources.get(dataSourceId)) {
            this._setupListDataSource(listId, 0);
        }
        this.dataSources.get(dataSourceId).increaseMaxPosition(position);
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
        const cell = this.getters.getCell(position);
        const sheetId = position.sheetId;
        if (cell && cell.isFormula) {
            const listFunction = getFirstListFunction(cell.compiledFormula.tokens);
            if (listFunction) {
                const content = astToFormula(listFunction.args[0]);
                return this.getters.evaluateFormula(sheetId, content).toString();
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
    getListCellValue(listId, position, fieldName) {
        return this.getters.getListDataSource(listId).getListCellValue(position, fieldName);
    }

    getListCurrency(listId, position, fieldName) {
        return this.getters.getListDataSource(listId).getListCurrency(position, fieldName);
    }

    /**
     * Get the currently selected list id
     * @returns {number|undefined} Id of the list, undefined if no one is selected
     */
    getSelectedListId() {
        return this.selectedListId;
    }

    /**
     * @param {string} id
     * @returns {import("@spreadsheet/list/list_data_source").default|undefined}
     */
    getListDataSource(id) {
        const dataSourceId = this._getListDataSourceId(id);
        return this.dataSources.get(dataSourceId);
    }

    /**
     * @param {string} id
     * @returns {Promise<import("@spreadsheet/list/list_data_source").default>}
     */
    async getAsyncListDataSource(id) {
        const dataSourceId = this._getListDataSourceId(id);
        await this.dataSources.load(dataSourceId);
        return this.getListDataSource(id);
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
}

ListUIPlugin.getters = [
    "getListComputedDomain",
    "getListCurrency",
    "getListHeaderValue",
    "getListIdFromPosition",
    "getListCellValue",
    "getSelectedListId",
    "getListDataSource",
    "getAsyncListDataSource",
];
