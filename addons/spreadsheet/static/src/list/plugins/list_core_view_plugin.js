import * as spreadsheet from "@odoo/o-spreadsheet";
import { getFirstListFunction } from "../list_helpers";
import { Domain } from "@web/core/domain";
import { ListDataSource } from "../list_data_source";
import { OdooCoreViewPlugin } from "@spreadsheet/plugins";
import { isDataSourceUrl, parseDataSourceUrl } from "../../data_sources/data_source_link";
import { ListPresentationLayer } from "../list_presentation";

const { astToFormula } = spreadsheet;
const { isMarkdownLink, parseMarkdownLink } = spreadsheet.links;

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
        "getListValuesAndFormats",
        "invalidateListsCache",
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
                    this._setupList(listId, 0);
                }
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
                const { listId, linesNumber } = cmd;
                this._setupList(listId, linesNumber);
                break;
            }
            case "DUPLICATE_ODOO_LIST": {
                this._setupList(cmd.newListId, 0);
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
                const listDefinition = this._getListModelDefinition(cmd.listId);
                this.lists[cmd.listId].updateDefinition(listDefinition);
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

                    const listDefinition = this._getListModelDefinition(cmd.listId);
                    this.lists[cmd.listId].updateDefinition(listDefinition);
                    this._addDomain(cmd.listId);
                }
                break;
            }
        }
    }

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    _setupList(listId, limit, definition) {
        if (!(listId in this.lists)) {
            definition = definition || this._getListModelDefinition(listId);
            const dataSource = new ListDataSource(this.custom, { ...definition, limit });
            this.lists[listId] = new ListPresentationLayer(
                this.getters,
                listId,
                definition,
                dataSource
            );
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
        this.lists[listId].addDomain(domain);
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
     * Refresh the cache of all the lists
     */
    _refreshOdooLists() {
        for (const listId of this.getters.getListIds()) {
            this.lists[listId].refresh();
        }
    }

    _getUnusedLists() {
        if (this.unusedLists !== undefined) {
            return this.unusedLists;
        }
        const unusedLists = new Set(this.getters.getListIds());
        for (const sheetId of this.getters.getSheetIds()) {
            for (const cell of this.getters.getCells(sheetId)) {
                const position = this.getters.getCellPosition(cell.id);
                const listId = this.getListIdFromPosition(position);
                if (listId) {
                    unusedLists.delete(listId);
                    if (!unusedLists.size) {
                        this.unusedLists = [];
                        return this.unusedLists;
                    }
                }
                if (isMarkdownLink(cell.content)) {
                    const { url } = parseMarkdownLink(cell.content);
                    if (isDataSourceUrl(url)) {
                        const [type, id] = parseDataSourceUrl(url);
                        if (type === "list") {
                            unusedLists.delete(id);
                            if (!unusedLists.size) {
                                this.unusedLists = [];
                                return this.unusedLists;
                            }
                        }
                    }
                }
            }
        }
        this.unusedLists = [...unusedLists];
        return this.unusedLists;
    }

    _getListModelDefinition(id) {
        const definition = this.getters.getListDefinition(id);
        return {
            metaData: {
                resModel: definition.model,
            },
            searchParams: {
                domain: definition.domain,
                context: definition.context,
                orderBy: definition.orderBy,
            },
            name: definition.name,
            columns: definition.columns,
        };
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
            const listFunction = getFirstListFunction(cell.compiledFormula, this.getters);
            if (listFunction) {
                const content = astToFormula(listFunction.args[0]);
                return this.getters.evaluateFormula(sheetId, content)?.toString();
            }
        }
        return undefined;
    }

    getListFieldFromPosition(position) {
        const listId = this.getListIdFromPosition(position);
        if (listId === undefined) {
            return undefined;
        }
        const cell = this.getters.getCorrespondingFormulaCell(position);
        if (!cell?.isFormula) {
            return undefined;
        }
        const { functionName, args } = getFirstListFunction(cell.compiledFormula, this.getters);
        const dataSource = this.getters.getListDataSource(listId);
        if (functionName === "ODOO.LIST") {
            const mainCell = this.getters.getCorrespondingFormulaCell(position);
            const mainPosition = this.getters.getCellPosition(mainCell.id);
            const colOffset = position.col - mainPosition.col;
            const fields = this.getters
                .getListDefinition(listId)
                .columns.filter((col) => !col.hidden);
            const fieldName = fields[colOffset]?.name;
            if (!fieldName) {
                return undefined;
            }
            return dataSource.getFields()[fieldName];
        }
        // ODOO.LIST.HEADER or ODOO.LIST.VALUE
        const fieldArg = functionName === "ODOO.LIST.HEADER" ? args[1] : args[2];
        if (!fieldArg || !dataSource.isValid()) {
            return undefined;
        }
        const fieldName = this.getters
            .evaluateFormula(position.sheetId, astToFormula(fieldArg))
            ?.toString();
        return dataSource.getFields()[fieldName];
    }

    getListSortDirection(position) {
        const listId = this.getListIdFromPosition(position);
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
        const listId = this.getListIdFromPosition(position);
        if (!listId) {
            return false;
        }
        const cell = this.getters.getCell(position);
        const mainCell = this.getters.getCorrespondingFormulaCell(position);
        if (!cell?.isFormula && !mainCell?.isFormula) {
            return false;
        }

        const dataSource = this.getListDataSource(listId);
        if (
            !(
                dataSource &&
                dataSource.isMetaDataLoaded() &&
                this.getListFieldFromPosition(position)?.sortable
            )
        ) {
            return false;
        }
        const { functionName } = getFirstListFunction(mainCell.compiledFormula, this.getters);

        if (functionName === "ODOO.LIST") {
            const mainPosition = this.getters.getCellPosition(mainCell.id);
            const rowOffset = position.row - mainPosition.row;
            return rowOffset === 0;
        }
        return functionName === "ODOO.LIST.HEADER";
    }

    /**
     * Get the value of a list header
     *
     * @param {string} listId Id of a list
     * @param {string} path
     */
    getListHeaderValue(listId, path) {
        return this.lists[listId].getListHeaderValue(path);
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
        const column = this.lists[listId].definition.columns.find((col) => col.name === path) || {
            name: path,
        };
        return this.lists[listId].getListCellValueAndFormat(column, position);
    }

    getListCurrency(listId, position, path, currentFieldName) {
        return this.lists[listId].getListCurrency(position, path, currentFieldName);
    }

    /**
     * @param {string} id
     * @returns {import("@spreadsheet/list/list_data_source").default|undefined}
     */
    getListDataSource(id) {
        return this.lists[id].dataSource;
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
        return (
            this._getUnusedLists().includes(listId) &&
            !this.getters.isDataSourceLinkedToChart("list", listId)
        );
    }

    getListValuesAndFormats(listId, rowCount) {
        return this.lists[listId].getListValuesAndFormats(rowCount);
    }

    invalidateListsCache() {
        for (const listId of this.getters.getListIds()) {
            this.lists[listId].invalidateCache();
        }
    }
}
