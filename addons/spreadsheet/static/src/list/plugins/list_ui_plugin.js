/** @odoo-module */

import spreadsheet from "../../o_spreadsheet/o_spreadsheet_extended";
import { getFirstListFunction } from "../list_helpers";

const { astToFormula } = spreadsheet;

/**
 * @typedef {import("./list_core_plugin").SpreadsheetList} SpreadsheetList
 */

export default class ListUIPlugin extends spreadsheet.UIPlugin {
    constructor(getters, history, dispatch, config, selection) {
        super(getters, history, dispatch, config, selection);
        /** @type {string} */
        this.selectedListId = undefined;
        this.env = config.evalContext.env;
    }

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "SELECT_ODOO_LIST":
                this._selectList(cmd.listId);
                break;
            case "ADD_LIST_DOMAIN":
                this._addDomain(cmd.id, cmd.domain);
                break;
            case "REFRESH_ODOO_LIST":
                this._refreshOdooList(cmd.listId);
                break;
            case "REFRESH_ALL_DATA_SOURCES":
                this._refreshOdooLists();
                break;
        }
    }

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Add an additional domain to a list
     *
     * @private
     *
     * @param {string} listId pivot id
     * @param {Array<Array<any>>} domain
     */
    _addDomain(listId, domain) {
        this.getters.getListDataSource(listId).addDomain(domain);
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
     * @param {string} sheetId Id of the sheet
     * @param {number} col Index of the col
     * @param {number} row Index of the row
     *
     * @returns {string|undefined}
     */
    getListIdFromPosition(sheetId, col, row) {
        const cell = this.getters.getCell(sheetId, col, row);
        if (cell && cell.isFormula()) {
            const listFunction = getFirstListFunction(cell.content);
            if (listFunction) {
                const content = astToFormula(listFunction.args[0]);
                return this.getters.evaluateFormula(content).toString();
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

    /**
     * Get the currently selected list id
     * @returns {number|undefined} Id of the list, undefined if no one is selected
     */
    getSelectedListId() {
        return this.selectedListId;
    }
}

ListUIPlugin.getters = [
    "getListComputedDomain",
    "getListHeaderValue",
    "getListIdFromPosition",
    "getListCellValue",
    "getSelectedListId",
];
