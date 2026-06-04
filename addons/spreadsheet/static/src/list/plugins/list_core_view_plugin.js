import * as spreadsheet from "@odoo/o-spreadsheet";
import { getFirstListFunction } from "../list_helpers";
import { Domain } from "@web/core/domain";
import { ListDataSource } from "../list_data_source";
import { OdooCoreViewPlugin } from "@spreadsheet/plugins";
import { isDataSourceUrl, parseDataSourceUrl } from "../../data_sources/data_source_link";

const { astToFormula, NotAvailableError, CircularDependencyError } = spreadsheet;
const { isMarkdownLink, parseMarkdownLink } = spreadsheet.links;
const { unquote, isMatrix, isEvaluationError } = spreadsheet.helpers;
/**
 * @typedef {import("./list_core_plugin").SpreadsheetList} SpreadsheetList
 */

export class ListCoreViewPlugin extends OdooCoreViewPlugin {
    static getters = /** @type {const} */ ([
        "getListComputedDomain",
        "getListHeaderValue",
        "getListIdFromPosition",
        "isDynamicList",
        "getListFieldFromPosition",
        "getListSortDirection",
        "getListFieldSortDirection",
        "isSortableListHeader",
        "getListCellValueAndFormat",
        "getListDataSource",
        "getAsyncListDataSource",
        "isListUnused",
        "getListValuesAndFormats",
    ]);
    constructor(config) {
        super(config);
        /** @type {string} */
        this.env = config.custom.env;

        /** @type {Record<string, ListDataSource>} */
        this.lists = {};

        this.custom = config.custom;
        this._pendingAddDomains = false;
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
                this._pendingAddDomains = true;
                break;
            case "UPDATE_ODOO_LIST":
            case "UPDATE_ODOO_LIST_DOMAIN": {
                const listDefinition = this._getListModelDefinition(cmd.listId);
                this.lists[cmd.listId].definition = listDefinition;
                this.lists[cmd.listId].dataSource.onDefinitionChange(listDefinition);
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
                    this.lists[cmd.listId].definition = listDefinition;
                    this.lists[cmd.listId].dataSource.onDefinitionChange(listDefinition);
                    this._addDomain(cmd.listId);
                }
                break;
            }
        }
    }

    finalize() {
        if (this._pendingAddDomains) {
            this._addDomains();
            this._pendingAddDomains = false;
        }
    }

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    _setupList(listId, limit) {
        if (!(listId in this.lists)) {
            const definition = this._getListModelDefinition(listId);
            const dataSource = new ListDataSource(this.custom, { ...definition, limit });
            this.lists[listId] = {
                id: listId,
                definition,
                dataSource,
            };
        }
        this._addDomain(listId);
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
        this.lists[listId].dataSource.addDomain(domain);
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
            this.lists[listId].dataSource.load({ reload: true });
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

    _computeCellValue(listId, column, position) {
        const formula = this.getters.getListCompiledColumnFormula(listId, column.name);
        const getSymbolValue = (symbol) => {
            symbol = unquote(symbol, "'");
            const symbolColumn = this.lists[listId].definition.columns.find(
                (col) => col.name === symbol
            );
            if (!symbolColumn) {
                return new NotAvailableError(`There is no '${symbol}' column in the list.`);
            } else if (symbolColumn.name === column.name) {
                return new CircularDependencyError();
            }
            if (symbolColumn && symbolColumn.computedBy) {
                return this._computeCellValue(listId, symbolColumn, position);
            }
            return this._getListCellValueAndFormat(listId, position, symbolColumn.name);
        };
        let result = this.getters.evaluateCompiledFormula(
            column.computedBy.sheetId,
            formula,
            getSymbolValue
        );
        if (isMatrix(result)) {
            result = result[0][0];
        }
        return result;
    }

    _getListCellValueAndFormat(listId, position, path) {
        const list = this.lists[listId];
        // shortcut to pre-fill the fetch list (spares a round of server call)
        list.dataSource.addFieldPathToFetch(path);
        const value = list.dataSource.getListCellValue(position, path);
        if (typeof value === "object" && isEvaluationError(value.value)) {
            return value;
        }
        const field = list.dataSource.getFieldFromFieldPath(path);
        const format = this._getListFormat(listId, position, path, field);
        return { value, format };
    }

    _getListFormat(listId, position, path, field) {
        const locale = this.getters.getLocale();
        switch (field?.type) {
            case "integer":
                return "0";
            case "float":
                return "#,##0.00";
            case "monetary": {
                const currency = this.lists[listId].dataSource.getListCurrency(
                    position,
                    path,
                    field.currency_field
                );
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
            const listFunction = getFirstListFunction(cell.compiledFormula, this.getters);
            if (listFunction) {
                const content = astToFormula(listFunction.args[0]);
                return this.getters.evaluateFormula(sheetId, content)?.toString();
            }
        }
        return undefined;
    }

    isDynamicList(position) {
        const cell = this.getters.getCorrespondingFormulaCell(position);
        if (cell && cell.isFormula) {
            const listFunction = getFirstListFunction(cell.compiledFormula, this.getters);
            if (listFunction) {
                return listFunction.functionName === "ODOO.LIST";
            }
        }
        return false;
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

    getListFieldSortDirection(position) {
        const listId = this.getListIdFromPosition(position);
        if (!listId) {
            return "none";
        }
        const field = this.getters.getListFieldFromPosition(position);
        if (!field) {
            return "none";
        }
        const definition = this.getters.getListDefinition(listId);
        const orderBy = definition.orderBy.find((order) => order.name === field.name);
        return orderBy ? (orderBy.asc ? "asc" : "desc") : "none";
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
        const columnDef = this.lists[listId].definition.columns.find((col) => col.name === path);

        if (columnDef?.string) {
            return { value: columnDef.string };
        }
        return this.lists[listId].dataSource.getListHeaderValue(path);
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
        if (column && column.computedBy) {
            return this._computeCellValue(listId, column, position);
        }
        return this._getListCellValueAndFormat(listId, position, column.name);
    }

    getListCurrency(listId, position, path, currentFieldName) {
        return this.lists[listId].dataSource.getListCurrency(position, path, currentFieldName);
    }

    /**
     * @param {string} listId
     * @returns {import("@spreadsheet/list/list_data_source").default|undefined}
     */
    getListDataSource(listId) {
        return this.lists[listId]?.dataSource;
    }

    /**
     * @param {string} listId
     * @returns {Promise<import("@spreadsheet/list/list_data_source").ListDataSource>}
     */
    async getAsyncListDataSource(listId) {
        const dataSource = this.getListDataSource(listId);
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
        if (rowCount === undefined) {
            throw new Error("The number of rows to fetch must be specified");
        }
        const list = this.lists[listId];
        const columns = list.definition.columns.filter((col) => !col.hidden);

        if (columns.length === 0) {
            return { value: this.getters.getListDisplayName(listId) };
        }

        const computedColumns = columns.filter((col) => !!col.computedBy);

        const symbolsInComputed = new Set(
            computedColumns.flatMap(
                (col) => this.getters.getListCompiledColumnFormula(listId, col.name).symbols
            )
        );

        const columnToFetch = [];
        for (const col of list.definition.columns) {
            if ((!col.hidden || symbolsInComputed.has(col.name)) && !col.computedBy) {
                columnToFetch.push(col);
            }
        }

        if (columnToFetch.length) {
            columnToFetch.forEach((col) => list.dataSource.addFieldPathToFetch(col.name));
            // triggers the fetch of the list values up to `rowCount` to fill the datasource cache (if not already done)
            list.dataSource.getListCellValue(rowCount, columnToFetch[0]?.name);
        }

        const numberRecordsToLoad = Math.min(list.dataSource.data.length, rowCount);
        const valuesAndFormats = [];
        for (const column of columns) {
            if (column.hidden) {
                continue;
            }
            const currentColumn = [];
            currentColumn.push(this.getListHeaderValue(listId, column.name));
            for (let position = 0; position < numberRecordsToLoad; position++) {
                if (column && column.computedBy) {
                    currentColumn.push(this._computeCellValue(listId, column, position));
                } else {
                    currentColumn.push(
                        this._getListCellValueAndFormat(listId, position, column.name)
                    );
                }
            }
            valuesAndFormats.push(currentColumn);
        }
        return valuesAndFormats;
    }
}
