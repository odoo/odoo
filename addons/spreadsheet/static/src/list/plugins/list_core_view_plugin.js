import * as spreadsheet from "@odoo/o-spreadsheet";
import { getFirstListFunction } from "../list_helpers";
import { Domain } from "@web/core/domain";
import { ListDataSource } from "../list_data_source";
import { OdooCoreViewPlugin } from "@spreadsheet/plugins";

const { astToFormula } = spreadsheet;
const { isEvaluationError } = spreadsheet.helpers;

/**
 * @typedef {import("./list_core_plugin").SpreadsheetList} SpreadsheetList
 */

export class ListCoreViewPlugin extends OdooCoreViewPlugin {
    static getters = /** @type {const} */ ([
        "getListComputedDomain",
        "getListHeaderValue",
        "getListIdFromPosition",
        "getListFieldFromPosition",
        "getListSortDirection",
        "isSortableListHeader",
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
                this._addDomains();
                break;
            case "UPDATE_ODOO_LIST":
            case "UPDATE_ODOO_LIST_DOMAIN": {
                const listDefinition = this.getters.getListModelDefinition(cmd.listId);
                const dataSourceId = this._getListDataSourceId(cmd.listId);
                this.lists[dataSourceId] = new ListDataSource(this.custom, listDefinition);
                this._addDomain(cmd.listId);
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
                    this._addDomain(cmd.listId);
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

    _getListFormat(listId, position, path, field) {
        const locale = this.getters.getLocale();
        switch (field?.type) {
            case "integer":
                return "0";
            case "float":
                return "#,##0.00";
            case "monetary": {
                const currency = this.getListCurrency(listId, position, path, field.currency_field);
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

    getListFieldFromPosition(position) {
        const listId = this.getters.getListIdFromPosition(position);
        if (listId === undefined) {
            return undefined;
        }
        const cell = this.getters.getCell(position);
        if (!cell?.isFormula) {
            return undefined;
        }
        const { functionName, args } = getFirstListFunction(cell.compiledFormula.tokens);
        const fieldArg = functionName === "ODOO.LIST.HEADER" ? args[1] : args[2];
        const dataSource = this.getters.getListDataSource(listId);
        if (!fieldArg || !dataSource.isValid()) {
            return undefined;
        }
        const fieldName = this.getters
            .evaluateFormula(position.sheetId, astToFormula(fieldArg))
            ?.toString();
        return dataSource.getFields()[fieldName];
    }

    getListSortDirection(position) {
        const listId = this.getters.getListIdFromPosition(position);
        if (!listId) {
            return "none";
        }
        const field = this.getters.getListFieldFromPosition(position);
        const orderBy = this.getters.getListDefinition(listId).orderBy[0];
        if (!orderBy || !field || orderBy.name !== field.name) {
            return "none";
        }
        return orderBy.asc ? "asc" : "desc";
    }

    isSortableListHeader(position) {
        const listId = this.getters.getListIdFromPosition(position);
        if (!listId) {
            return false;
        }
        const cell = this.getters.getCell(position);
        if (!cell?.isFormula) {
            return false;
        }
        const { functionName } = getFirstListFunction(cell.compiledFormula.tokens);
        const dataSource = this.getters.getListDataSource(listId);
        return (
            functionName === "ODOO.LIST.HEADER" &&
            dataSource.isMetaDataLoaded() &&
            this.getters.getListFieldFromPosition(position)?.sortable
        );
    }

    /**
     * Get the value of a list header
     *
     * @param {string} listId Id of a list
     * @param {string} path
     */
    getListHeaderValue(listId, path) {
        return this.getters.getListDataSource(listId).getListHeaderValue(path);
    }

    /**
     * Get the value for a field of a record in the list
     * @param {string} listId Id of the list
     * @param {number} position Position of the record in the list
     * @param {string} path Path of the field
     *
     * @returns {string|undefined}
     */
    getListCellValueAndFormat(listId, position, path) {
        const dataSource = this.getters.getListDataSource(listId);
        dataSource.addFieldPathToFetch(path);
        const value = dataSource.getListCellValue(position, path);
        if (typeof value === "object" && isEvaluationError(value.value)) {
            return value;
        }
        const field = dataSource.getFieldFromFieldPath(path);
        const format = this._getListFormat(listId, position, path, field);
        return { value, format };
    }

    getListCurrency(listId, position, path, currentFieldName) {
        return this.getters
            .getListDataSource(listId)
            .getListCurrency(position, path, currentFieldName);
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

    isListUnused(listId) {
        return this._getUnusedLists().includes(listId);
    }
}
