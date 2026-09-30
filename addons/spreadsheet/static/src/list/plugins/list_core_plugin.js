import { CommandResult } from "../../o_spreadsheet/cancelled_reason";
import { helpers } from "@odoo/o-spreadsheet";
import { Domain } from "@web/core/domain";
import { deepCopy } from "@web/core/utils/objects";
import { OdooCorePlugin } from "@spreadsheet/plugins";

const { getMaxObjectId } = helpers;

/**
 * @typedef {Object} ListDefinition
 * @property {Array<string>} columns
 * @property {Object} context
 * @property {Array<Array<string>>} domain
 * @property {string} id The id of the list
 * @property {string} model The technical name of the model we are listing
 * @property {string} name Name of the list
 * @property {Array<string>} orderBy
 * @property {string} actionXmlId
 *
 * @typedef {Object} List
 * @property {string} id
 * @property {string} dataSourceId
 * @property {ListDefinition} definition
 */

export class ListCorePlugin extends OdooCorePlugin {
    static getters = /** @type {const} */ ([
        "getListDisplayName",
        "getListDefinition",
        "getListModelDefinition",
        "getListIds",
        "getListName",
        "getNextListId",
        "isExistingList",
    ]);
    constructor(config) {
        super(config);

        this.nextId = 1;
        /** @type {Object.<string, List>} */
        this.lists = {};
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
            case "DUPLICATE_ODOO_LIST":
                if (!this.lists[cmd.listId]) {
                    return CommandResult.ListIdNotFound;
                }
                if (cmd.newListId !== this.nextId.toString()) {
                    return CommandResult.InvalidNextId;
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
            case "UPDATE_ODOO_LIST":
            case "UPDATE_ODOO_LIST_DOMAIN":
                if (!(cmd.listId in this.lists)) {
                    return CommandResult.ListIdNotFound;
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
            case "INSERT_ODOO_LIST": {
                const { sheetId, col, row, id, definition, linesNumber, columns } = cmd;
                const anchor = [col, row];
                this._addList(id, definition);
                this._insertList(sheetId, anchor, id, linesNumber, columns);
                this.history.update("nextId", parseInt(id, 10) + 1);
                break;
            }
            case "DUPLICATE_ODOO_LIST": {
                const { listId, newListId, duplicatedListName } = cmd;
                const duplicatedList = deepCopy(this.lists[listId].definition);
                duplicatedList.name = duplicatedListName ?? duplicatedList.name + " (copy)";
                this._addList(newListId, duplicatedList);
                this.history.update("nextId", parseInt(newListId, 10) + 1);
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
                break;
            }
            case "UPDATE_ODOO_LIST": {
                this.history.update("lists", cmd.listId, "definition", cmd.list);
                break;
            }
        }
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

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
        return this.lists[id].definition.name;
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
            domain: def.searchParams.domain,
            model: def.metaData.resModel,
            context: { ...def.searchParams.context },
            orderBy: [...def.searchParams.orderBy],
            id,
            name: def.name,
            actionXmlId: def.actionXmlId,
        };
    }

    getListModelDefinition(id) {
        return this.lists[id].definition;
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

    _addList(id, definition) {
        const lists = { ...this.lists };
        lists[id] = {
            id,
            definition,
        };
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
            const content = column.string
                ? `=ODOO.LIST.HEADER(${id},"${column.name}","${column.string}")`
                : `=ODOO.LIST.HEADER(${id},"${column.name}")`;
            this.dispatch("UPDATE_CELL", {
                sheetId,
                col,
                row,
                content,
            });
            col++;
        }
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
                    actionXmlId: list.actionXmlId,
                    name: list.name,
                };
                this._addList(id, definition);
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
            data.lists[id].domain = new Domain(data.lists[id].domain).toJson();
        }
        data.listNextId = this.nextId;
    }
}
