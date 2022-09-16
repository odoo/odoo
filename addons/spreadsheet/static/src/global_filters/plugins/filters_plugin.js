/** @odoo-module */

/**
 * @typedef {"year"|"month"|"quarter"|"relative"} RangeType
 *
/**
 * @typedef {Object} FilterMatchingField
 * @property {string} field name of the field
 * @property {string} type type of the field
 * @property {number} [offset] offset to apply to the field (for date filters)
 *
 * @typedef {Object} GlobalFilter
 * @property {string} id
 * @property {string} label
 * @property {string} type "text" | "date" | "relation"
 * @property {RangeType} rangeType
 * @property {Record<string, FilterMatchingField>} pivotFields
 * @property {Record<string, FilterMatchingField>} listFields
 * @property {Record<string, FilterMatchingField>} graphFields
 * @property {string|Array<string>|Object} defaultValue Default Value
 * @property {number} [modelID] ID of the related model
 * @property {string} [modelName] Name of the related model
 */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import CommandResult from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { checkFiltersTypeValueCombination } from "@spreadsheet/global_filters/helpers";

export default class FiltersPlugin extends spreadsheet.CorePlugin {
    constructor() {
        super(...arguments);
        /** @type {Object.<string, GlobalFilter>} */
        this.globalFilters = {};
    }

    /**
     * Check if the given command can be dispatched
     *
     * @param {Object} cmd Command
     */
    allowDispatch(cmd) {
        switch (cmd.type) {
            case "EDIT_GLOBAL_FILTER":
                if (!this.getGlobalFilter(cmd.id)) {
                    return CommandResult.FilterNotFound;
                } else if (this._isDuplicatedLabel(cmd.id, cmd.filter.label)) {
                    return CommandResult.DuplicatedFilterLabel;
                }
                return checkFiltersTypeValueCombination(cmd.filter.type, cmd.filter.defaultValue);
            case "REMOVE_GLOBAL_FILTER":
                if (!this.getGlobalFilter(cmd.id)) {
                    return CommandResult.FilterNotFound;
                }
                break;
            case "ADD_GLOBAL_FILTER":
                if (this._isDuplicatedLabel(cmd.id, cmd.filter.label)) {
                    return CommandResult.DuplicatedFilterLabel;
                }
                return checkFiltersTypeValueCombination(cmd.filter.type, cmd.filter.defaultValue);
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
            case "ADD_GLOBAL_FILTER":
                this._addGlobalFilter(cmd.filter);
                break;
            case "EDIT_GLOBAL_FILTER":
                this._editGlobalFilter(cmd.id, cmd.filter);
                break;
            case "REMOVE_GLOBAL_FILTER":
                this._removeGlobalFilter(cmd.id);
                break;
            case "REMOVE_PIVOT":
                this._removeMatchingField("pivot", cmd.pivotId);
                break;
            case "REMOVE_ODOO_LIST":
                this._removeMatchingField("list", cmd.listId);
                break;
            case "DELETE_FIGURE":
                this._removeMatchingField("graph", cmd.id);
                break;
        }
    }

    // ---------------------------------------------------------------------
    // Getters
    // ---------------------------------------------------------------------

    /**
     * Retrieve the global filter with the given id
     *
     * @param {string} id
     * @returns {GlobalFilter|undefined} Global filter
     */
    getGlobalFilter(id) {
        return this.globalFilters[id];
    }

    /**
     * Get the field name on which the global filter is applied for a pivot
     *
     * @param {string} filterId Id of the filter
     * @param {string} pivotId Id of the pivot
     * @returns {FilterMatchingField|undefined}
     */
    getGlobalFilterFieldPivot(filterId, pivotId) {
        return this.getGlobalFilter(filterId).pivotFields[pivotId];
    }

    /**
     * Get the field name on which the global filter is applied for a list
     *
     * @param {string} filterId Id of the filter
     * @param {string} listId Id of the list
     * @returns {FilterMatchingField|undefined}
     */
    getGlobalFilterFieldList(filterId, listId) {
        return this.getGlobalFilter(filterId).listFields[listId];
    }

    /**
     * Get the field name on which the global filter is applied for a graph
     *
     * @param {string} filterId Id of the filter
     * @param {string} graphId Id of the Graph
     * @returns {FilterMatchingField|undefined}
     */
    getGlobalFilterFieldGraph(filterId, graphId) {
        return this.getGlobalFilter(filterId).graphFields[graphId];
    }

    /**
     * Get the global filter with the given name
     *
     * @param {string} label Label
     *
     * @returns {GlobalFilter|undefined}
     */
    getGlobalFilterLabel(label) {
        return this.getGlobalFilters().find((filter) => filter.label === label);
    }

    /**
     * Retrieve all the global filters
     *
     * @returns {Array<GlobalFilter>} Array of Global filters
     */
    getGlobalFilters() {
        return Object.values(this.globalFilters);
    }

    /**
     * Get the default value of a global filter
     *
     * @param {string} id Id of the filter
     *
     * @returns {string|Array<string>|Object}
     */
    getGlobalFilterDefaultValue(id) {
        return this.getGlobalFilter(id).defaultValue;
    }

    // ---------------------------------------------------------------------
    // Handlers
    // ---------------------------------------------------------------------

    /**
     * Add a global filter
     *
     * @param {GlobalFilter} filter
     */
    _addGlobalFilter(filter) {
        const globalFilters = { ...this.globalFilters };
        globalFilters[filter.id] = filter;
        this.history.update("globalFilters", globalFilters);
    }
    /**
     * Remove a global filter
     *
     * @param {number} id Id of the filter to remove
     */
    _removeGlobalFilter(id) {
        const globalFilters = { ...this.globalFilters };
        delete globalFilters[id];
        this.history.update("globalFilters", globalFilters);
    }
    /**
     * Edit a global filter
     *
     * @param {number} id Id of the filter to update
     * @param {GlobalFilter} newFilter
     */
    _editGlobalFilter(id, newFilter) {
        const currentLabel = this.getGlobalFilter(id).label;
        const globalFilters = { ...this.globalFilters };
        newFilter.id = id;
        globalFilters[id] = newFilter;
        this.history.update("globalFilters", globalFilters);
        const newLabel = this.getGlobalFilter(id).label;
        if (currentLabel !== newLabel) {
            this._updateFilterLabelInFormulas(currentLabel, newLabel);
        }
    }

    /**
     * @param {"pivot" | "list" | "graph"} dataSourceType
     * @param {string} dataSourceId
     */
    _removeMatchingField(dataSourceType, dataSourceId) {
        for (const filter of this.getGlobalFilters()) {
            this.history.update(
                "globalFilters",
                filter.id,
                `${dataSourceType}Fields`,
                dataSourceId,
                undefined
            );
        }
    }

    // ---------------------------------------------------------------------
    // Import/Export
    // ---------------------------------------------------------------------

    /**
     * Import the filters
     *
     * @param {Object} data
     */
    import(data) {
        for (const globalFilter of data.globalFilters || []) {
            this.globalFilters[globalFilter.id] = globalFilter;
        }
    }
    /**
     * Export the filters
     *
     * @param {Object} data
     */
    export(data) {
        data.globalFilters = this.getGlobalFilters().map((filter) => ({
            ...filter,
        }));
    }

    // ---------------------------------------------------------------------
    // Global filters
    // ---------------------------------------------------------------------

    /**
     * Update all ODOO.FILTER.VALUE formulas to reference a filter
     * by its new label.
     *
     * @param {string} currentLabel
     * @param {string} newLabel
     */
    _updateFilterLabelInFormulas(currentLabel, newLabel) {
        const sheetIds = this.getters.getSheetIds();
        currentLabel = currentLabel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        for (const sheetId of sheetIds) {
            for (const cell of Object.values(this.getters.getCells(sheetId))) {
                if (cell.isFormula()) {
                    const newContent = cell.content.replace(
                        new RegExp(`FILTER\\.VALUE\\(\\s*"${currentLabel}"\\s*\\)`, "g"),
                        `FILTER.VALUE("${newLabel}")`
                    );
                    if (newContent !== cell.content) {
                        const { col, row } = this.getters.getCellPosition(cell.id);
                        this.dispatch("UPDATE_CELL", {
                            sheetId,
                            content: newContent,
                            col,
                            row,
                        });
                    }
                }
            }
        }
    }

    /**
     * Return true if the label is duplicated
     *
     * @param {string | undefined} filterId
     * @param {string} label
     * @returns {boolean}
     */
    _isDuplicatedLabel(filterId, label) {
        return (
            this.getGlobalFilters().findIndex(
                (filter) => (!filterId || filter.id !== filterId) && filter.label === label
            ) > -1
        );
    }
}

FiltersPlugin.getters = [
    "getGlobalFilter",
    "getGlobalFilters",
    "getGlobalFilterDefaultValue",
    "getGlobalFilterLabel",
    "getGlobalFilterFieldPivot",
    "getGlobalFilterFieldList",
    "getGlobalFilterFieldGraph",
];
