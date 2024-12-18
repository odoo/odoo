/** @odoo-module */

import { FILTER_DATE_OPTION, monthsOptions } from "@spreadsheet/assets_backend/constants";
import { Domain } from "@web/core/domain";
import { NO_RECORD_AT_THIS_POSITION } from "../pivot_model";
import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { pivotTimeAdapter } from "../pivot_time_adapters";

const { DateTime } = luxon;

/**
 * @typedef {import("./pivot_core_plugin").OdooPivotDefinition} OdooPivotDefinition
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").FieldMatching} FieldMatching
 * @typedef {import("@odoo/o-spreadsheet").Token} Token
 */

/**
 * Convert pivot period to the related filter value
 *
 * @param {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").RangeType} timeRange
 * @param {string|number} value
 * @returns {object}
 */
function pivotPeriodToFilterValue(timeRange, value) {
    // reuse the same logic as in `parseAccountingDate`?
    if (typeof value === "number") {
        value = value.toString(10);
    }
    if (
        value === "false" || // the value "false" is the default value when there is no data for a group header
        typeof value !== "string"
    ) {
        // anything else then a string at this point is incorrect, so no filtering
        return undefined;
    }

    const yearValue = value.split("/").at(-1);
    if (!yearValue) {
        return undefined;
    }
    const yearOffset = yearValue - DateTime.now().year;
    switch (timeRange) {
        case "year":
            return {
                yearOffset,
            };
        case "month": {
            const month = value.includes("/") ? Number.parseInt(value.split("/")[0]) : -1;
            if (!(month in monthsOptions)) {
                return { yearOffset, period: undefined };
            }
            return {
                yearOffset,
                period: monthsOptions[month - 1].id,
            };
        }
        case "quarter": {
            const quarter = value.includes("/") ? Number.parseInt(value.split("/")[0]) : -1;
            if (!(quarter in FILTER_DATE_OPTION.quarter)) {
                return { yearOffset, period: undefined };
            }
            return {
                yearOffset,
                period: FILTER_DATE_OPTION.quarter[quarter - 1],
            };
        }
    }
}

export class PivotUIGlobalFilterPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ ([
        "getPivotComputedDomain",
        "getFiltersMatchingPivotArgs",
    ]);
    constructor(config) {
        super(config);
        /** @type {string} */
        this.selection.observe(this, {
            handleEvent: this.handleEvent.bind(this),
        });

        globalFiltersFieldMatchers["pivot"] = {
            ...globalFiltersFieldMatchers["pivot"],
            waitForReady: () => this._getPivotsWaitForReady(),
            getFields: (pivotId) => this.getters.getPivot(pivotId).getFields(),
        };
    }

    handleEvent(event) {
        if (!this.getters.isDashboard()) {
            return;
        }
        switch (event.type) {
            case "ZonesSelected": {
                const sheetId = this.getters.getActiveSheetId();
                const { col, row } = event.anchor.cell;
                const cell = this.getters.getCell({ sheetId, col, row });
                if (cell !== undefined && cell.content.startsWith("=ODOO.PIVOT.HEADER(")) {
                    const filters = this._getFiltersMatchingPivot(sheetId, cell.compiledFormula.tokens);
                    this.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters });
                }
                break;
            }
        }
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
            case "ADD_GLOBAL_FILTER":
            case "EDIT_GLOBAL_FILTER":
            case "REMOVE_GLOBAL_FILTER":
            case "SET_GLOBAL_FILTER_VALUE":
            case "CLEAR_GLOBAL_FILTER_VALUE":
                this._addDomains();
                break;
            case "UPDATE_PIVOT":
            case "UPDATE_ODOO_PIVOT_DOMAIN":
                this._addDomain(cmd.pivotId);
                break;
            case "UNDO":
            case "REDO": {
                if (
                    cmd.commands.find((command) =>
                        [
                            "ADD_GLOBAL_FILTER",
                            "EDIT_GLOBAL_FILTER",
                            "REMOVE_GLOBAL_FILTER",
                            "UPDATE_ODOO_PIVOT_DOMAIN",
                            "UPDATE_PIVOT",
                        ].includes(command.type)
                    )
                ) {
                    this._addDomains();
                }
                break;
            }
        }
    }

    // ---------------------------------------------------------------------
    // Getters
    // ---------------------------------------------------------------------

    /**
     * Get the computed domain of a pivot
     * CLEAN ME not used outside of tests
     * @param {string} pivotId Id of the pivot
     * @returns {Array}
     */
    getPivotComputedDomain(pivotId) {
        return this.getters.getPivot(pivotId).getComputedDomain();
    }

    /**
     * Get the filter impacted by a pivot formula's argument
     * @param {Token[]} tokens Formula of the pivot cell
     *
     * @returns {Array<Object>}
     */
    _getFiltersMatchingPivot(sheetId, tokens) {
        const functionDescription = this.getters.getFirstPivotFunction(sheetId, tokens);
        if (!functionDescription) {
            return [];
        }
        const { args } = functionDescription;
        if (args.length <= 2) {
            return [];
        }
        const formulaId = args[0];
        const pivotId = this.getters.getPivotId(formulaId);
        return this.getFiltersMatchingPivotArgs(pivotId, args);
    }

    /**
     * Get the filter impacted by a pivot
     */
    getFiltersMatchingPivotArgs(pivotId, domainArgs) {
        const argField = domainArgs[domainArgs.length - 2];
        if (argField === "measure" || !argField) {
            return [];
        }
        const filters = this.getters.getGlobalFilters();
        const matchingFilters = [];

        for (const filter of filters) {
            const dataSource = this.getters.getPivot(pivotId);
            const { field, aggregateOperator: time } = dataSource.parseGroupField(argField);
            const pivotFieldMatching = this.getters.getPivotFieldMatching(pivotId, filter.id);
            if (pivotFieldMatching && pivotFieldMatching.chain === field.name) {
                let value = dataSource.getLastPivotGroupValue(domainArgs.slice(-2));
                if (value === NO_RECORD_AT_THIS_POSITION) {
                    continue;
                }
                let transformedValue;
                const currentValue = this.getters.getGlobalFilterValue(filter.id);
                switch (filter.type) {
                    case "date":
                        if (filter.rangeType === "fixedPeriod" && time) {
                            if (value === "false") {
                                transformedValue = undefined;
                            }
                            else {
                                transformedValue = pivotPeriodToFilterValue(time, value);
                                if (JSON.stringify(transformedValue) === JSON.stringify(currentValue)) {
                                    transformedValue = undefined;
                                }
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
     * @param {import("../../data_sources/metadata_repository").Field} field
     * @param {"day" | "week" | "month" | "quarter" | "year"} aggregateOperator
     * @returns {string | undefined}
     */
    _getFieldFormat(field, aggregateOperator) {
        switch (field.type) {
            case "integer":
                return "0";
            case "float":
                return "#,##0.00";
            case "monetary":
                return this.getters.getCompanyCurrencyFormat() || "#,##0.00";
            case "date":
            case "datetime": {
                const timeAdapter = pivotTimeAdapter(aggregateOperator);
                return timeAdapter.getFormat(this.getters.getLocale());
            }
            default:
                return undefined;
        }
    }

    /**
     * Add an additional domain to a pivot
     *
     * @private
     *
     * @param {string} pivotId pivot id
     */
    _addDomain(pivotId) {
        const domainList = [];
        for (const [filterId, fieldMatch] of Object.entries(
            this.getters.getPivotFieldMatch(pivotId)
        )) {
            domainList.push(this.getters.getGlobalFilterDomain(filterId, fieldMatch));
        }
        const domain = Domain.combine(domainList, "AND").toString();
        this.getters.getPivot(pivotId).addDomain(domain);
    }

    /**
     * Add an additional domain to all pivots
     *
     * @private
     *
     */
    _addDomains() {
        for (const pivotId of this.getters.getPivotIds()) {
            this._addDomain(pivotId);
        }
    }

    /**
     *
     * @return {Promise[]}
     */
    _getPivotsWaitForReady() {
        return this.getters
            .getPivotIds()
            .map((pivotId) => this.getters.getPivot(pivotId).loadMetadata());
    }
}
