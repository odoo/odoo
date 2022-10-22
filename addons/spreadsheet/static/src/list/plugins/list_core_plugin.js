/** @odoo-module */

import spreadsheet from "../../o_spreadsheet/o_spreadsheet_extended";
import CommandResult from "../../o_spreadsheet/cancelled_reason";
import { getMaxObjectId } from "../../helpers/helpers";
import ListDataSource from "../list_data_source";
import { TOP_LEVEL_STYLE } from "../../helpers/constants";
import { _t } from "@web/core/l10n/translation";
import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
import { sprintf } from "@web/core/utils/strings";
import { checkFilterFieldMatching } from "@spreadsheet/global_filters/helpers";

/**
 * @typedef {Object} ListDefinition
 * @property {Array<string>} columns
 * @property {Object} context
 * @property {Array<Array<string>>} domain
 * @property {string} id The id of the list
 * @property {string} model The technical name of the model we are listing
 * @property {string} name Name of the list
 * @property {Array<string>} orderBy
 *
 * @typedef {Object} List
 * @property {string} id
 * @property {string} dataSourceId
 * @property {ListDefinition} definition
 * @property {Object} fieldMatching
 *
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").FieldMatching} FieldMatching
 */

const { CorePlugin } = spreadsheet;

export default class ListCorePlugin extends CorePlugin {
    constructor(config) {
        super(config);
        this.dataSources = config.external.dataSources;

        this.nextId = 1;
        /** @type {Object.<string, List>} */
        this.lists = {};

        globalFiltersFieldMatchers["list"] = {
            geIds: () => this.getters.getListIds(),
            getDisplayName: (listId) => this.getters.getListName(listId),
            getTag: (listId) => sprintf(_t("List #%s"), listId),
            getFieldMatching: (listId, filterId) => this.getListFieldMatching(listId, filterId),
            waitForReady: () => this.getListsWaitForReady(),
            getModel: (listId) => this.getListDefinition(listId).model,
            getFields: (listId) => this.getListDataSource(listId).getFields(),
        };
    }

    allowDispatch(cmd) {
        switch (cmd.type) {
            case "INSERT_ODOO_LIST":
                if (cmd.id !== this.nextId.toString()) {
                    return CommandResult.InvalidNextId;
                }
                if (this.lists[cmd.id]) {
                    return CommandResult.ListIdDuplicated;
                }
                break;
            case "RENAME_ODOO_LIST":
                if (!(cmd.listId in this.lists)) {
                    return CommandResult.ListIdNotFound;
                }
                if (cmd.name === "") {
                    return CommandResult.EmptyName;
                }
                break;
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
                if (cmd.list) {
                    return checkFilterFieldMatching(cmd.list);
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
            case "INSERT_ODOO_LIST": {
                const { sheetId, col, row, id, definition, dataSourceId, linesNumber, columns } =
                    cmd;
                const anchor = [col, row];
                this._addList(id, definition, dataSourceId, linesNumber);
                this._insertList(sheetId, anchor, id, linesNumber, columns);
                this.nextId = parseInt(id, 10) + 1;
                break;
            }
            case "RE_INSERT_ODOO_LIST": {
                const { sheetId, col, row, id, linesNumber, columns } = cmd;
                const anchor = [col, row];
                this._insertList(sheetId, anchor, id, linesNumber, columns);
                break;
            }
            case "RENAME_ODOO_LIST": {
                this.history.update("lists", cmd.listId, "definition", "name", cmd.name);
                break;
            }
            case "REMOVE_ODOO_LIST": {
                const lists = { ...this.lists };
                delete lists[cmd.listId];
                this.history.update("lists", lists);
                break;
            }
            case "UPDATE_ODOO_LIST_DOMAIN": {
                this.history.update(
                    "lists",
                    cmd.listId,
                    "definition",
                    "searchParams",
                    "domain",
                    cmd.domain
                );
                const list = this.lists[cmd.listId];
                this.dataSources.add(list.dataSourceId, ListDataSource, list.definition);
                break;
            }
            case "UNDO":
            case "REDO": {
                const domainEditionCommands = cmd.commands.filter(
                    (cmd) => cmd.type === "UPDATE_ODOO_LIST_DOMAIN"
                );
                for (const cmd of domainEditionCommands) {
                    const list = this.lists[cmd.listId];
                    this.dataSources.add(list.dataSourceId, ListDataSource, list.definition);
                }
                break;
            }
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
                if (cmd.list) {
                    this._setListFieldMatching(cmd.filter.id, cmd.list);
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
     * @returns {import("@spreadsheet/list/list_data_source").default|undefined}
     */
    getListDataSource(id) {
        const dataSourceId = this.lists[id].dataSourceId;
        return this.dataSources.get(dataSourceId);
    }

    /**
     * @param {string} id
     * @returns {string}
     */
    getListDisplayName(id) {
        return `(#${id}) ${this.getListName(id)}`;
    }

    /**
     * @param {string} id
     * @returns {string}
     */
    getListName(id) {
        return _t(this.lists[id].definition.name);
    }

    /**
     * @param {string} id
     * @returns {string}
     */
    getListFieldMatch(id) {
        return this.lists[id].fieldMatching;
    }

    /**
     * @param {string} id
     * @returns {Promise<import("@spreadsheet/list/list_data_source").default>}
     */
    async getAsyncListDataSource(id) {
        const dataSourceId = this.lists[id].dataSourceId;
        await this.dataSources.load(dataSourceId);
        return this.getListDataSource(id);
    }

    /**
     * Retrieve all the list ids
     *
     * @returns {Array<string>} list ids
     */
    getListIds() {
        return Object.keys(this.lists);
    }

    /**
     * Retrieve the next available id for a new list
     *
     * @returns {string} id
     */
    getNextListId() {
        return this.nextId.toString();
    }

    /**
     * @param {string} id
     * @returns {ListDefinition}
     */
    getListDefinition(id) {
        const def = this.lists[id].definition;
        return {
            columns: [...def.metaData.columns],
            domain: [...def.searchParams.domain],
            model: def.metaData.resModel,
            context: { ...def.searchParams.context },
            orderBy: [...def.searchParams.orderBy],
            id,
            name: def.name,
        };
    }

    /**
     * Check if an id is an id of an existing list
     *
     * @param {string} id Id of the list
     *
     * @returns {boolean}
     */
    isExistingList(id) {
        return id in this.lists;
    }

    // ---------------------------------------------------------------------
    // Private
    // ---------------------------------------------------------------------

    /**
     *
     * @return {Promise[]}
     */
    getListsWaitForReady() {
        return this.getListIds().map((ListId) => this.getListDataSource(ListId).loadMetadata());
    }

    /**
     * Get the current FieldMatching on a list
     *
     * @param {string} listId
     * @param {string} filterId
     */
    getListFieldMatching(listId, filterId) {
        return this.lists[listId].fieldMatching[filterId];
    }

    /**
     * Sets the current FieldMatching on a list
     *
     * @param {string} filterId
     * @param {Record<string,FieldMatching>} listFieldMatches
     */
    _setListFieldMatching(filterId, listFieldMatches) {
        const lists = { ...this.lists };
        for (const [listId, fieldMatch] of Object.entries(listFieldMatches)) {
            lists[listId].fieldMatching[filterId] = fieldMatch;
        }
        this.history.update("lists", lists);
    }

    _onFilterDeletion(filterId) {
        const lists = { ...this.lists };
        for (const listId in lists) {
            this.history.update("lists", listId, "fieldMatching", filterId, undefined);
        }
    }

    _addList(id, definition, dataSourceId, limit, fieldMatching = {}) {
        const lists = { ...this.lists };
        lists[id] = {
            id,
            definition,
            dataSourceId,
            fieldMatching,
        };

        if (!this.dataSources.contains(dataSourceId)) {
            this.dataSources.add(dataSourceId, ListDataSource, {
                ...definition,
                limit,
            });
        }
        this.history.update("lists", lists);
    }

    /**
     * Build an Odoo List
     * @param {string} sheetId Id of the sheet
     * @param {[number,number]} anchor Top-left cell in which the list should be inserted
     * @param {string} id Id of the list
     * @param {number} linesNumber Number of records to insert
     * @param {Array<Object>} columns Columns ({name, type})
     */
    _insertList(sheetId, anchor, id, linesNumber, columns) {
        this._resizeSheet(sheetId, anchor, columns.length, linesNumber + 1);
        this._insertHeaders(sheetId, anchor, id, columns);
        this._insertValues(sheetId, anchor, id, columns, linesNumber);
    }

    _insertHeaders(sheetId, anchor, id, columns) {
        let [col, row] = anchor;
        for (const column of columns) {
            this.dispatch("UPDATE_CELL", {
                sheetId,
                col,
                row,
                content: `=ODOO.LIST.HEADER(${id},"${column.name}")`,
            });
            col++;
        }
        this.dispatch("SET_FORMATTING", {
            sheetId,
            style: TOP_LEVEL_STYLE,
            target: [
                {
                    top: anchor[1],
                    bottom: anchor[1],
                    left: anchor[0],
                    right: anchor[0] + columns.length - 1,
                },
            ],
        });
    }

    _insertValues(sheetId, anchor, id, columns, linesNumber) {
        let col = anchor[0];
        let row = anchor[1] + 1;
        for (let i = 1; i <= linesNumber; i++) {
            col = anchor[0];
            for (const column of columns) {
                this.dispatch("UPDATE_CELL", {
                    sheetId,
                    col,
                    row,
                    content: `=ODOO.LIST(${id},${i},"${column.name}")`,
                });
                col++;
            }
            row++;
        }
    }

    /**
     * Resize the sheet to match the size of the listing. Columns and/or rows
     * could be added to be sure to insert the entire sheet.
     *
     * @param {string} sheetId Id of the sheet
     * @param {[number,number]} anchor Anchor of the list [col,row]
     * @param {number} columns Number of columns of the list
     * @param {number} rows Number of rows of the list
     */
    _resizeSheet(sheetId, anchor, columns, rows) {
        const numberCols = this.getters.getNumberCols(sheetId);
        const deltaCol = numberCols - anchor[0];
        if (deltaCol < columns) {
            this.dispatch("ADD_COLUMNS_ROWS", {
                dimension: "COL",
                base: numberCols - 1,
                sheetId: sheetId,
                quantity: columns - deltaCol,
                position: "after",
            });
        }
        const numberRows = this.getters.getNumberRows(sheetId);
        const deltaRow = numberRows - anchor[1];
        if (deltaRow < rows) {
            this.dispatch("ADD_COLUMNS_ROWS", {
                dimension: "ROW",
                base: numberRows - 1,
                sheetId: sheetId,
                quantity: rows - deltaRow,
                position: "after",
            });
        }
    }

    // ---------------------------------------------------------------------
    // Import/Export
    // ---------------------------------------------------------------------

    /**
     * Import the lists
     *
     * @param {Object} data
     */
    import(data) {
        if (data.lists) {
            for (const [id, list] of Object.entries(data.lists)) {
                const definition = {
                    metaData: {
                        resModel: list.model,
                        columns: list.columns,
                    },
                    searchParams: {
                        domain: list.domain,
                        context: list.context,
                        orderBy: list.orderBy,
                    },
                    name: list.name,
                };
                this._addList(id, definition, this.uuidGenerator.uuidv4(), 0, list.fieldMatching);
            }
        }
        this.nextId = data.listNextId || getMaxObjectId(this.lists) + 1;
    }
    /**
     * Export the lists
     *
     * @param {Object} data
     */
    export(data) {
        data.lists = {};
        for (const id in this.lists) {
            data.lists[id] = JSON.parse(JSON.stringify(this.getListDefinition(id)));
            data.lists[id].fieldMatching = this.lists[id].fieldMatching;
        }
        data.listNextId = this.nextId;
    }
}

ListCorePlugin.getters = [
    "getListDataSource",
    "getListDisplayName",
    "getAsyncListDataSource",
    "getListDefinition",
    "getListIds",
    "getListName",
    "getNextListId",
    "isExistingList",
    "getListFieldMatch",
    "getListFieldMatching",
];
