/** @odoo-module */

import { _t } from "web.core";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { getFirstPivotFunction } from "../pivot_helpers";
import { FILTER_DATE_OPTION, monthsOptions } from "@spreadsheet/assets_backend/constants";

const { astToFormula } = spreadsheet;
const { DateTime } = luxon;

/**
 * Convert pivot period to the related filter value
 *
 * @param {import("@spreadsheet/global_filters/plugins/filters_plugin").RangeType} timeRange
 * @param {string} value
 * @returns {object}
 */
function pivotPeriodToFilterValue(timeRange, value) {
    // reuse the same logic as in `parseAccountingDate`?
    const yearOffset = (value.split("/").pop() | 0) - DateTime.now().year;
    switch (timeRange) {
        case "year":
            return {
                yearOffset,
            };
        case "month": {
            const month = value.split("/")[0] | 0;
            return {
                yearOffset,
                period: monthsOptions[month - 1].id,
            };
        }
        case "quarter": {
            const quarter = value.split("/")[0] | 0;
            return {
                yearOffset,
                period: FILTER_DATE_OPTION.quarter[quarter - 1],
            };
        }
    }
}

export default class PivotUIPlugin extends spreadsheet.UIPlugin {
    constructor() {
        super(...arguments);
        /** @type {string} */
        this.selectedPivotId = undefined;
        this.selection.observe(this, {
            handleEvent: this.handleEvent.bind(this),
        });
    }

    handleEvent(event) {
        if (!this.getters.isDashboard()) {
            return;
        }
        switch (event.type) {
            case "ZonesSelected": {
                const sheetId = this.getters.getActiveSheetId();
                const { col, row } = event.anchor.cell;
                const cell = this.getters.getCell(sheetId, col, row);
                if (cell !== undefined && cell.content.startsWith("=ODOO.PIVOT.HEADER(")) {
                    const filters = this.getFiltersMatchingPivot(cell.content);
                    this.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters });
                }
                break;
            }
        }
    }

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "SELECT_PIVOT":
                this.selectedPivotId = cmd.pivotId;
                break;
            case "ADD_PIVOT_DOMAIN":
                this._addDomain(cmd.id, cmd.domain);
                break;
            case "REFRESH_PIVOT":
                this._refreshOdooPivot(cmd.id);
                break;
            case "REFRESH_ALL_DATA_SOURCES":
                this._refreshOdooPivots();
                break;
        }
    }

    // ---------------------------------------------------------------------
    // Getters
    // ---------------------------------------------------------------------

    /**
     * Retrieve the pivotId of the current selected cell
     *
     * @returns {string}
     */
    getSelectedPivotId() {
        return this.selectedPivotId;
    }

    /**
     * Get the id of the pivot at the given position. Returns undefined if there
     * is no pivot at this position
     *
     * @param {string} sheetId Id of the sheet
     * @param {number} col Index of the col
     * @param {number} row Index of the row
     *
     * @returns {string|undefined}
     */
    getPivotIdFromPosition(sheetId, col, row) {
        const cell = this.getters.getCell(sheetId, col, row);
        if (cell && cell.isFormula()) {
            const pivotFunction = getFirstPivotFunction(cell.content);
            if (pivotFunction) {
                const content = astToFormula(pivotFunction.args[0]);
                return this.getters.evaluateFormula(content).toString();
            }
        }
        return undefined;
    }

    /**
     * Get the computed domain of a pivot
     * CLEAN ME not used outside of tests
     * @param {string} pivotId Id of the pivot
     * @returns {Array}
     */
    getPivotComputedDomain(pivotId) {
        return this.getters.getPivotDataSource(pivotId).getComputedDomain();
    }

    /**
     * Return all possible values in the pivot for a given field.
     *
     * @param {string} pivotId Id of the pivot
     * @param {string} fieldName
     * @returns {Array<string>}
     */
    getPivotGroupByValues(pivotId, fieldName) {
        return this.getters.getPivotDataSource(pivotId).getPossibleValuesForGroupBy(fieldName);
    }

    /**
     * Get the value of a pivot header
     *
     * @param {string} pivotId Id of a pivot
     * @param {Array<string>} domain Domain
     */
    getDisplayedPivotHeaderValue(pivotId, domain) {
        const dataSource = this.getters.getPivotDataSource(pivotId);
        dataSource.markAsHeaderUsed(domain);
        const len = domain.length;
        if (len === 0) {
            return _t("Total");
        }
        return dataSource.getDisplayedPivotHeaderValue(domain);
    }

    /**
     * Get the value for a pivot cell
     *
     * @param {string} pivotId Id of a pivot
     * @param {string} measure Field name of the measures
     * @param {Array<string>} domain Domain
     *
     * @returns {string|number|undefined}
     */
    getPivotCellValue(pivotId, measure, domain) {
        const dataSource = this.getters.getPivotDataSource(pivotId);
        dataSource.markAsValueUsed(domain, measure);
        return dataSource.getPivotCellValue(measure, domain);
    }

    /**
     * Get the filter impacted by a pivot formula's argument
     *
     * @param {string} formula Formula of the pivot cell
     *
     * @returns {Array<Object>}
     */
    getFiltersMatchingPivot(formula) {
        const functionDescription = getFirstPivotFunction(formula);
        if (!functionDescription) {
            return [];
        }
        const { args } = functionDescription;
        const evaluatedArgs = args
            .map(astToFormula)
            .map((arg) => this.getters.evaluateFormula(arg));
        const pivotId = evaluatedArgs[0];
        const argField = evaluatedArgs[evaluatedArgs.length - 2];
        const filters = this.getters.getGlobalFilters();
        const matchingFilters = [];

        for (const filter of filters) {
            const dataSource = this.getters.getPivotDataSource(pivotId);
            const { field, aggregateOperator: time } = dataSource.parseGroupField(argField);
            if (filter.pivotFields[pivotId].field === field.name) {
                let value = dataSource.getPivotHeaderValue(evaluatedArgs.slice(1));
                let transformedValue;
                const currentValue = this.getters.getGlobalFilterValue(filter.id);
                switch (filter.type) {
                    case "date":
                        if (time === filter.rangeType) {
                            transformedValue = pivotPeriodToFilterValue(time, value);
                            if (JSON.stringify(transformedValue) === JSON.stringify(currentValue)) {
                                transformedValue = undefined;
                            }
                        } else {
                            continue;
                        }
                        break;
                    case "relation":
                        if (typeof value == "string") {
                            value = Number(value);
                            if (Number.isNaN(value)) {
                                break;
                            }
                        }
                        if (JSON.stringify(currentValue) !== `[${value}]`) {
                            transformedValue = [value];
                        }
                        break;
                    case "text":
                        if (currentValue !== value) {
                            transformedValue = value;
                        }
                        break;
                }
                matchingFilters.push({ filterId: filter.id, value: transformedValue });
            }
        }
        return matchingFilters;
    }

    // ---------------------------------------------------------------------
    // Private
    // ---------------------------------------------------------------------

    /**
     * Refresh the cache of a pivot
     *
     * @param {string} pivotId Id of the pivot
     */
    _refreshOdooPivot(pivotId) {
        const dataSource = this.getters.getPivotDataSource(pivotId);
        dataSource.clearUsedValues();
        dataSource.load({ reload: true });
    }

    /**
     * Refresh the cache of all the lists
     */
    _refreshOdooPivots() {
        for (const pivotId of this.getters.getPivotIds()) {
            this._refreshOdooPivot(pivotId, false);
        }
    }

    /**
     * Add an additional domain to a pivot
     *
     * @private
     *
     * @param {string} pivotId pivot id
     * @param {Array<Array<any>>} domain
     */
    _addDomain(pivotId, domain) {
        this.getters.getPivotDataSource(pivotId).addDomain(domain);
    }
}

PivotUIPlugin.getters = [
    "getSelectedPivotId",
    "getPivotComputedDomain",
    "getDisplayedPivotHeaderValue",
    "getPivotIdFromPosition",
    "getPivotCellValue",
    "getPivotGroupByValues",
    "getFiltersMatchingPivot",
];
