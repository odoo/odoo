/** @odoo-module */

/**
 * @typedef {import("@spreadsheet/data_sources/metadata_repository").Field} Field
 * @typedef {import("./global_filters_core_plugin").GlobalFilter} GlobalFilter
 * @typedef {import("./global_filters_core_plugin").FieldMatching} FieldMatching
 
 */

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { Domain } from "@web/core/domain";
import { constructDateRange, getPeriodOptions, QUARTER_OPTIONS } from "@web/search/utils/dates";

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import CommandResult from "@spreadsheet/o_spreadsheet/cancelled_reason";

import { isEmpty } from "@spreadsheet/helpers/helpers";
import { FILTER_DATE_OPTION } from "@spreadsheet/assets_backend/constants";
import {
    checkFiltersTypeValueCombination,
    getRelativeDateDomain,
} from "@spreadsheet/global_filters/helpers";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";

const { DateTime } = luxon;

const MONTHS = {
    january: { value: 1, granularity: "month" },
    february: { value: 2, granularity: "month" },
    march: { value: 3, granularity: "month" },
    april: { value: 4, granularity: "month" },
    may: { value: 5, granularity: "month" },
    june: { value: 6, granularity: "month" },
    july: { value: 7, granularity: "month" },
    august: { value: 8, granularity: "month" },
    september: { value: 9, granularity: "month" },
    october: { value: 10, granularity: "month" },
    november: { value: 11, granularity: "month" },
    december: { value: 12, granularity: "month" },
};

const { UuidGenerator, createEmptyExcelSheet } = spreadsheet.helpers;
const uuidGenerator = new UuidGenerator();

export default class GlobalFiltersUIPlugin extends spreadsheet.UIPlugin {
    constructor(getters, history, dispatch, config) {
        super(getters, history, dispatch, config);
        this.orm = config.evalContext.env ? config.evalContext.env.services.orm : undefined;
        /**
         * Cache record display names for relation filters.
         * For each filter, contains a promise resolving to
         * the list of display names.
         */
        this.recordsDisplayName = {};
        /** @type {Object.<string, string|Array<string>|Object>} */
        this.values = {};
    }

    /**
     * Check if the given command can be dispatched
     *
     * @param {Object} cmd Command
     */
    allowDispatch(cmd) {
        switch (cmd.type) {
            case "SET_GLOBAL_FILTER_VALUE": {
                const filter = this.getters.getGlobalFilter(cmd.id);
                if (!filter) {
                    return CommandResult.FilterNotFound;
                }
                return checkFiltersTypeValueCombination(filter.type, cmd.value);
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
            case "ADD_GLOBAL_FILTER":
                this.recordsDisplayName[cmd.filter.id] = cmd.filter.defaultValueDisplayNames;
                break;
            case "EDIT_GLOBAL_FILTER":
                if (this.values[cmd.id] && this.values[cmd.id].rangeType !== cmd.filter.rangeType) {
                    delete this.values[cmd.id];
                }
                this.recordsDisplayName[cmd.filter.id] = cmd.filter.defaultValueDisplayNames;
                break;
            case "SET_GLOBAL_FILTER_VALUE":
                this.recordsDisplayName[cmd.id] = cmd.displayNames;
                this._setGlobalFilterValue(cmd.id, cmd.value);
                break;
            case "SET_MANY_GLOBAL_FILTER_VALUE":
                for (const filter of cmd.filters) {
                    if (filter.value !== undefined) {
                        this.dispatch("SET_GLOBAL_FILTER_VALUE", {
                            id: filter.filterId,
                            value: filter.value,
                        });
                    } else {
                        this.dispatch("CLEAR_GLOBAL_FILTER_VALUE", { id: filter.filterId });
                    }
                }
                break;
            case "REMOVE_GLOBAL_FILTER":
                delete this.recordsDisplayName[cmd.id];
                delete this.values[cmd.id];
                break;
            case "CLEAR_GLOBAL_FILTER_VALUE":
                this.recordsDisplayName[cmd.id] = [];
                this._clearGlobalFilterValue(cmd.id);
                break;
        }
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /**
     * @param {string} filterId
     * @param {FieldMatching} fieldMatching
     *
     * @return {Domain}
     */
    getGlobalFilterDomain(filterId, fieldMatching) {
        /** @type {GlobalFilter} */
        const filter = this.getters.getGlobalFilter(filterId);
        if (!filter) {
            return new Domain();
        }
        switch (filter.type) {
            case "text":
                return this._getTextDomain(filter, fieldMatching);
            case "date":
                return this._getDateDomain(filter, fieldMatching);
            case "relation":
                return this._getRelationDomain(filter, fieldMatching);
        }
    }

    /**
     * Get the current value of a global filter
     *
     * @param {string} filterId Id of the filter
     *
     * @returns {string|Array<string>|Object} value Current value to set
     */
    getGlobalFilterValue(filterId) {
        const filter = this.getters.getGlobalFilter(filterId);

        const value = filterId in this.values ? this.values[filterId].value : filter.defaultValue;

        const preventAutomaticValue =
            this.values[filterId] &&
            this.values[filterId].value &&
            this.values[filterId].value.preventAutomaticValue;
        const defaultsToCurrentPeriod = !preventAutomaticValue && filter.defaultsToCurrentPeriod;

        if (filter.type === "date" && isEmpty(value) && defaultsToCurrentPeriod) {
            return this._getValueOfCurrentPeriod(filterId);
        }

        return value;
    }

    /**
     * @param {string} id Id of the filter
     *
     * @returns { boolean } true if the given filter is active
     */
    isGlobalFilterActive(id) {
        const { type } = this.getters.getGlobalFilter(id);
        const value = this.getGlobalFilterValue(id);
        switch (type) {
            case "text":
                return value;
            case "date":
                return (
                    value &&
                    (typeof value === "string" || value.yearOffset !== undefined || value.period)
                );
            case "relation":
                return value && value.length;
        }
    }

    /**
     * Get the number of active global filters
     *
     * @returns {number}
     */
    getActiveFilterCount() {
        return this.getters
            .getGlobalFilters()
            .filter((filter) => this.isGlobalFilterActive(filter.id)).length;
    }

    getFilterDisplayValue(filterName) {
        const filter = this.getters.getGlobalFilterLabel(filterName);
        if (!filter) {
            throw new Error(sprintf(_t(`Filter "%s" not found`), filterName));
        }
        const value = this.getGlobalFilterValue(filter.id);
        switch (filter.type) {
            case "text":
                return value || "";
            case "date": {
                if (value && typeof value === "string") {
                    const type = RELATIVE_DATE_RANGE_TYPES.find((type) => type.type === value);
                    if (!type) {
                        return "";
                    }
                    return type.description.toString();
                }
                if (!value || value.yearOffset === undefined) {
                    return "";
                }
                const periodOptions = getPeriodOptions(DateTime.local());
                const year = String(DateTime.local().year + value.yearOffset);
                const period = periodOptions.find(({ id }) => value.period === id);
                let periodStr = period && period.description;
                // Named months aren't in getPeriodOptions
                if (!period) {
                    periodStr =
                        MONTHS[value.period] && String(MONTHS[value.period].value).padStart(2, "0");
                }
                return periodStr ? periodStr + "/" + year : year;
            }
            case "relation":
                if (!value || !this.orm) {
                    return "";
                }
                if (!this.recordsDisplayName[filter.id]) {
                    this.orm.call(filter.modelName, "name_get", [value]).then((result) => {
                        const names = result.map(([, name]) => name);
                        this.recordsDisplayName[filter.id] = names;
                        this.dispatch("EVALUATE_CELLS", {
                            sheetId: this.getters.getActiveSheetId(),
                        });
                    });
                    return "";
                }
                return this.recordsDisplayName[filter.id].join(", ");
        }
    }

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Set the current value of a global filter
     *
     * @param {string} id Id of the filter
     * @param {string|Array<string>|Object} value Current value to set
     */
    _setGlobalFilterValue(id, value) {
        this.values[id] = { value: value, rangeType: this.getters.getGlobalFilter(id).rangeType };
    }

    /**
     * Get the filter value corresponding to the current period, depending of the type of range of the filter.
     * For example if rangeType === "month", the value will be the current month of the current year.
     *
     * @param {string} filterId a global filter
     * @return {Object} filter value
     */
    _getValueOfCurrentPeriod(filterId) {
        const filter = this.getters.getGlobalFilter(filterId);
        const rangeType = filter.rangeType;
        switch (rangeType) {
            case "year":
                return { yearOffset: 0 };
            case "month": {
                const month = new Date().getMonth() + 1;
                const period = Object.entries(MONTHS).find((item) => item[1].value === month)[0];
                return { yearOffset: 0, period };
            }
            case "quarter": {
                const quarter = Math.floor(new Date().getMonth() / 3);
                const period = FILTER_DATE_OPTION.quarter[quarter];
                return { yearOffset: 0, period };
            }
        }
        return {};
    }

    /**
     * Set the current value to empty values which functionally deactivate the filter
     *
     * @param {string} id Id of the filter
     */
    _clearGlobalFilterValue(id) {
        const { type, rangeType } = this.getters.getGlobalFilter(id);
        let value;
        switch (type) {
            case "text":
                value = "";
                break;
            case "date":
                value = { yearOffset: undefined, preventAutomaticValue: true };
                break;
            case "relation":
                value = [];
                break;
        }
        this.values[id] = { value, rangeType };
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Get the domain relative to a date field
     *
     * @private
     *
     * @param {GlobalFilter} filter
     * @param {FieldMatching} fieldMatching
     *
     * @returns {Domain}
     */
    _getDateDomain(filter, fieldMatching) {
        let granularity;
        const value = this.getGlobalFilterValue(filter.id);
        if (!value || !fieldMatching.chain) {
            return new Domain();
        }
        const field = fieldMatching.chain;
        const type = fieldMatching.type;
        const offset = fieldMatching.offset || 0;
        const now = DateTime.local();

        if (filter.rangeType === "relative") {
            return getRelativeDateDomain(now, offset, value, field, type);
        }
        if (value.yearOffset === undefined) {
            return new Domain();
        }

        const setParam = { year: now.year };
        const yearOffset = value.yearOffset || 0;
        const plusParam = {
            years: filter.rangeType === "year" ? yearOffset + offset : yearOffset,
        };
        if (!value.period || value.period === "empty") {
            granularity = "year";
        } else {
            switch (filter.rangeType) {
                case "month":
                    granularity = "month";
                    setParam.month = MONTHS[value.period].value;
                    plusParam.month = offset;
                    break;
                case "quarter":
                    granularity = "quarter";
                    setParam.quarter = QUARTER_OPTIONS[value.period].setParam.quarter;
                    plusParam.quarter = offset;
                    break;
            }
        }
        return constructDateRange({
            referenceMoment: now,
            fieldName: field,
            fieldType: type,
            granularity,
            setParam,
            plusParam,
        }).domain;
    }

    /**
     * Get the domain relative to a text field
     *
     * @private
     *
     * @param {GlobalFilter} filter
     * @param {FieldMatching} fieldMatching
     *
     * @returns {Domain}
     */
    _getTextDomain(filter, fieldMatching) {
        const value = this.getGlobalFilterValue(filter.id);
        if (!value || !fieldMatching.chain) {
            return new Domain();
        }
        const field = fieldMatching.chain;
        return new Domain([[field, "ilike", value]]);
    }

    /**
     * Get the domain relative to a relation field
     *
     * @private
     *
     * @param {GlobalFilter} filter
     * @param {FieldMatching} fieldMatching
     *
     * @returns {Domain}
     */
    _getRelationDomain(filter, fieldMatching) {
        const values = this.getGlobalFilterValue(filter.id);
        if (!values || values.length === 0 || !fieldMatching.chain) {
            return new Domain();
        }
        const field = fieldMatching.chain;
        return new Domain([[field, "in", values]]);
    }

    /**
     * Adds all active filters (and their values) at the time of export in a dedicated sheet
     *
     * @param {Object} data
     */
    exportForExcel(data) {
        if (this.getters.getGlobalFilters().length === 0) {
            return;
        }
        const styles = Object.entries(data.styles);
        let titleStyleId =
            styles.findIndex((el) => JSON.stringify(el[1]) === JSON.stringify({ bold: true })) + 1;

        if (titleStyleId <= 0) {
            titleStyleId = styles.length + 1;
            data.styles[styles.length + 1] = { bold: true };
        }

        const cells = {};
        cells["A1"] = { content: "Filter", style: titleStyleId };
        cells["B1"] = { content: "Value", style: titleStyleId };
        let row = 2;
        for (const filter of this.getters.getGlobalFilters()) {
            const content = this.getFilterDisplayValue(filter.label);
            cells[`A${row}`] = { content: filter.label };
            cells[`B${row}`] = { content };
            row++;
        }
        data.sheets.push({
            ...createEmptyExcelSheet(uuidGenerator.uuidv4(), _t("Active Filters")),
            cells,
            colNumber: 2,
            rowNumber: this.getters.getGlobalFilters().length + 1,
        });
    }
}

GlobalFiltersUIPlugin.getters = [
    "getFilterDisplayValue",
    "getGlobalFilterDomain",
    "getGlobalFilterValue",
    "getActiveFilterCount",
    "isGlobalFilterActive",
];
