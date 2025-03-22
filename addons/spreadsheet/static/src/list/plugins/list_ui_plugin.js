/** @odoo-module */

import spreadsheet from "../../o_spreadsheet/o_spreadsheet_extended";
import { getFirstListFunction } from "../list_helpers";
import { Domain } from "@web/core/domain";

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

    beforeHandle(cmd) {
        switch (cmd.type) {
            case "START":
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
            case "UPDATE_ODOO_LIST_DOMAIN":
                this._addDomain(cmd.listId);
                break;
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
            case "REMOVE_GLOBAL_FILTER":
            case "SET_GLOBAL_FILTER_VALUE":
            case "CLEAR_GLOBAL_FILTER_VALUE":
                this._addDomains();
                break;
            case "UNDO":
            case "REDO":
                if (
                    cmd.commands.find((command) =>
                        [
                            "ADD_GLOBAL_FILTER",
                            "EDIT_GLOBAL_FILTER",
                            "REMOVE_GLOBAL_FILTER",
                            "UPDATE_ODOO_LIST_DOMAIN",
                        ].includes(command.type)
                    )
                ) {
                    this._addDomains();
                }
                if (!this.getters.getListIds().length) {
                    this.selectedListId = undefined;
                }
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
