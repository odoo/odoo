/** @ts-check */

/**
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 * @typedef {import("@spreadsheet").DateGlobalFilter} DateGlobalFilter
 * @typedef {import("@spreadsheet").RelationalGlobalFilter} RelationalGlobalFilter
 */

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { Domain } from "@web/core/domain";
import { user } from "@web/core/user";
import { constructDateRange, QUARTER_OPTIONS } from "@web/search/utils/dates";

import { EvaluationError, helpers } from "@odoo/o-spreadsheet";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";

import { isEmpty } from "@spreadsheet/helpers/helpers";
import { FILTER_DATE_OPTION } from "@spreadsheet/assets_backend/constants";
import {
    checkFilterValueIsValid,
    getRelativeDateDomain,
} from "@spreadsheet/global_filters/helpers";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { getItemId } from "../../helpers/model";
import { serializeDateTime, serializeDate } from "@web/core/l10n/dates";

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

const { UuidGenerator, createEmptyExcelSheet, createEmptySheet, toXC, toNumber } = helpers;
const uuidGenerator = new UuidGenerator();

export class GlobalFiltersUIPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ ([
        "exportSheetWithActiveFilters",
        "getFilterDisplayValue",
        "getGlobalFilterDomain",
        "getGlobalFilterValue",
        "getActiveFilterCount",
        "isGlobalFilterActive",
        "getTextFilterOptions",
        "getTextFilterOptionsFromRange",
    ]);
    constructor(config) {
        super(config);
        this.orm = config.custom.env?.services.orm;
        this.odooDataProvider = config.custom.odooDataProvider;
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
     * @param {import("@spreadsheet").AllCommand} cmd Command
     */
    allowDispatch(cmd) {
        switch (cmd.type) {
            case "SET_GLOBAL_FILTER_VALUE": {
                const filter = this.getters.getGlobalFilter(cmd.id);
                if (!filter) {
                    return CommandResult.FilterNotFound;
                }
                if (!checkFilterValueIsValid(filter, cmd.value)) {
                    return CommandResult.InvalidValueTypeCombination;
                }
                break;
            }
        }
        return CommandResult.Success;
    }

    /**
     * Handle a spreadsheet command
     *
     * @param {import("@spreadsheet").AllCommand} cmd
     */
    handle(cmd) {
        switch (cmd.type) {
            case "ADD_GLOBAL_FILTER":
                this.recordsDisplayName[cmd.filter.id] =
                    cmd.filter.type === "relation"
                        ? cmd.filter.defaultValueDisplayNames
                        : undefined;
                break;
            case "EDIT_GLOBAL_FILTER": {
                const filter = cmd.filter;
                const id = filter.id;
                if (
                    filter.type === "date" &&
                    this.values[id] &&
                    this.values[id].rangeType !== filter.rangeType
                ) {
                    delete this.values[id];
                } else if (!checkFilterValueIsValid(filter, this.values[id]?.value)) {
                    delete this.values[id];
                }
                this.recordsDisplayName[id] =
                    filter.type === "relation" ? filter.defaultValueDisplayNames : undefined;
                break;
            }
            case "SET_GLOBAL_FILTER_VALUE":
                this.recordsDisplayName[cmd.id] = cmd.displayNames;
                if (!cmd.value) {
                    this._clearGlobalFilterValue(cmd.id);
                } else {
                    this._setGlobalFilterValue(cmd.id, cmd.value);
                }
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

        const value = filterId in this.values ? this.values[filterId].value : undefined;
        const preventAutomaticValue = this.values[filterId]?.value?.preventAutomaticValue;
        if (filter.type === "date" && filter.rangeType === "from_to") {
            return value || { from: undefined, to: undefined };
        }
        const defaultValue = (!preventAutomaticValue && filter.defaultValue) || undefined;
        if (filter.type === "date" && preventAutomaticValue) {
            return undefined;
        }
        if (filter.type === "date" && isEmpty(value) && defaultValue) {
            return this._getValueOfCurrentPeriod(filterId);
        }
        if (filter.type === "relation" && preventAutomaticValue) {
            return [];
        }
        if (filter.type === "relation" && isEmpty(value) && defaultValue === "current_user") {
            return [user.userId];
        }
        if (filter.type === "text" && preventAutomaticValue) {
            return "";
        }
        return value || defaultValue;
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
                    (typeof value === "string" ||
                        value.yearOffset !== undefined ||
                        value.period ||
                        value.from ||
                        value.to)
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
            throw new EvaluationError(sprintf(_t(`Filter "%s" not found`), filterName));
        }
        const value = this.getGlobalFilterValue(filter.id);
        switch (filter.type) {
            case "text":
                return [[{ value: value || "" }]];
            case "date": {
                if (filter.rangeType === "from_to") {
                    const locale = this.getters.getLocale();
                    const from = {
                        value: value.from ? toNumber(value.from, locale) : "",
                        format: locale.dateFormat,
                    };
                    const to = {
                        value: value.to ? toNumber(value.to, locale) : "",
                        format: locale.dateFormat,
                    };
                    return [[from], [to]];
                }
                if (value && typeof value === "string") {
                    const type = RELATIVE_DATE_RANGE_TYPES.find((type) => type.type === value);
                    if (!type) {
                        return [[{ value: "" }]];
                    }
                    return [[{ value: type.description.toString() }]];
                }
                if (!value || value.yearOffset === undefined) {
                    return [[{ value: "" }]];
                }
                const year = String(DateTime.local().year + value.yearOffset);
                const period = QUARTER_OPTIONS[value.period];
                let periodStr = period && "Q" + period.setParam.quarter; // we do not want the translated value (like T1 in French)
                // Named months aren't in QUARTER_OPTIONS
                if (!period) {
                    periodStr =
                        MONTHS[value.period] && String(MONTHS[value.period].value).padStart(2, "0");
                }
                return [[{ value: periodStr ? periodStr + "/" + year : year }]];
            }
            case "relation":
                if (!value?.length || !this.orm) {
                    return [[{ value: "" }]];
                }
                if (!this.recordsDisplayName[filter.id]) {
                    const promise = this.orm
                        .call(filter.modelName, "read", [value, ["display_name"]])
                        .then((result) => {
                            const names = result.map(({ display_name }) => display_name);
                            this.recordsDisplayName[filter.id] = names;
                        });
                    this.odooDataProvider.notifyWhenPromiseResolves(promise);
                    return [[{ value: "" }]];
                }
                return [[{ value: this.recordsDisplayName[filter.id].join(", ") }]];
        }
    }

    /**
     * Returns the possible values a text global filter can take
     * if the values are restricted by a range of allowed values
     * @param {string} filterId
     * @returns {{value: string, formattedValue: string}[]}
     */
    getTextFilterOptions(filterId) {
        const filter = this.getters.getGlobalFilter(filterId);
        if (filter.type !== "text" || !filter.rangeOfAllowedValues) {
            return [];
        }
        const additionOptions = [
            // add the current value because it might not be in the range
            // if the range cells changed in the meantime
            this.getGlobalFilterValue(filterId),
            filter.defaultValue,
        ];
        const options = this.getTextFilterOptionsFromRange(
            filter.rangeOfAllowedValues,
            additionOptions
        );
        return options;
    }

    /**
     * Returns the possible values a text global filter can take from a range
     * or any addition raw string value. Removes duplicates and empty string values.
     * @param {object} range
     * @param {string[]} additionalOptionValues
     */
    getTextFilterOptionsFromRange(range, additionalOptionValues = []) {
        const cells = this.getters.getEvaluatedCellsInZone(range.sheetId, range.zone);
        const uniqueFormattedValues = new Set();
        const uniqueValues = new Set();
        const allowedValues = cells
            .filter((cell) => !["empty", "error"].includes(cell.type) && cell.value !== "")
            .map((cell) => ({
                value: cell.value.toString(),
                formattedValue: cell.formattedValue,
            }))
            .filter((cell) => {
                if (uniqueFormattedValues.has(cell.formattedValue)) {
                    return false;
                }
                uniqueFormattedValues.add(cell.formattedValue);
                uniqueValues.add(cell.value);
                return true;
            });
        const additionalOptions = additionalOptionValues
            .map((value) => ({ value, formattedValue: value }))
            .filter((cell) => {
                if (cell.value === undefined || cell.value === "" || uniqueValues.has(cell.value)) {
                    return false;
                }
                uniqueValues.add(cell.value);
                return true;
            });
        return allowedValues.concat(additionalOptions);
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
        const filter = this.getters.getGlobalFilter(id);
        this.values[id] = {
            value: value,
            rangeType: filter.type === "date" ? filter.rangeType : undefined,
        };
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
        switch (filter.defaultValue) {
            case "this_year":
                return { yearOffset: 0 };
            case "this_month": {
                const month = new Date().getMonth() + 1;
                const period = Object.entries(MONTHS).find((item) => item[1].value === month)[0];
                return { yearOffset: 0, period };
            }
            case "this_quarter": {
                const quarter = Math.floor(new Date().getMonth() / 3);
                const period = FILTER_DATE_OPTION.quarter[quarter];
                return { yearOffset: 0, period };
            }
        }
        return filter.defaultValue;
    }

    /**
     * Set the current value to empty values which functionally deactivate the filter
     *
     * @param {string} id Id of the filter
     */
    _clearGlobalFilterValue(id) {
        const filter = this.getters.getGlobalFilter(id);
        let value;
        switch (filter.type) {
            case "text":
                value = { preventAutomaticValue: true };
                break;
            case "date":
                value = { preventAutomaticValue: true };
                break;
            case "relation":
                value = { preventAutomaticValue: true };
                break;
        }
        this.values[id] = {
            value,
            rangeType: filter.type === "date" ? filter.rangeType : undefined,
        };
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Get the domain relative to a date field
     *
     * @private
     *
     * @param {DateGlobalFilter} filter
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
        const type = /** @type {"date" | "datetime"} */ (fieldMatching.type);
        const offset = fieldMatching.offset || 0;
        const now = DateTime.local();

        if (filter.rangeType === "from_to") {
            const serialize = type === "datetime" ? serializeDateTime : serializeDate;
            const from = value.from && serialize(DateTime.fromISO(value.from).startOf("day"));
            const to = value.to && serialize(DateTime.fromISO(value.to).endOf("day"));
            if (from && to) {
                return new Domain(["&", [field, ">=", from], [field, "<=", to]]);
            }
            if (from) {
                return new Domain([[field, ">=", from]]);
            }
            if (to) {
                return new Domain([[field, "<=", to]]);
            }
            return new Domain();
        }

        if (filter.rangeType === "relative") {
            return getRelativeDateDomain(now, offset, value, field, type);
        }
        const noPeriod = !value.period || value.period === "empty";
        const noYear = value.yearOffset === undefined;
        if (noPeriod && noYear) {
            return new Domain();
        }
        const setParam = { year: now.year };
        const yearOffset = value.yearOffset || 0;
        const plusParam = { years: yearOffset };
        if (noPeriod) {
            granularity = "year";
            plusParam.years += offset;
        } else {
            // value.period is can be "first_quarter", "second_quarter", etc. or
            // full month name (e.g. "january", "february", "march", etc.)
            granularity = value.period.endsWith("_quarter") ? "quarter" : "month";
            switch (granularity) {
                case "month":
                    setParam.month = MONTHS[value.period].value;
                    plusParam.month = offset;
                    break;
                case "quarter":
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
     * @param {RelationalGlobalFilter} filter
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
        const operator = filter.includeChildren ? "child_of" : "in";
        return new Domain([[field, operator, values]]);
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
        this.exportSheetWithActiveFilters(data);
        data.sheets[data.sheets.length - 1] = {
            ...createEmptyExcelSheet(uuidGenerator.uuidv4(), _t("Active Filters")),
            ...data.sheets.at(-1),
        };
    }

    exportSheetWithActiveFilters(data) {
        if (this.getters.getGlobalFilters().length === 0) {
            return;
        }
        const styleId = getItemId({ bold: true }, data.styles);

        const cells = {};
        cells["A1"] = { content: "Filter", style: styleId };
        cells["B1"] = { content: "Value", style: styleId };
        let numberOfCols = 2; // at least 2 cols (filter title and filter value)
        let filterRowIndex = 1; // first row is the column titles
        for (const filter of this.getters.getGlobalFilters()) {
            cells[`A${filterRowIndex + 1}`] = { content: filter.label };
            const result = this.getFilterDisplayValue(filter.label);
            for (const colIndex in result) {
                numberOfCols = Math.max(numberOfCols, Number(colIndex) + 2);
                for (const rowIndex in result[colIndex]) {
                    const cell = result[colIndex][rowIndex];
                    if (cell.value === undefined) {
                        continue;
                    }
                    const xc = toXC(Number(colIndex) + 1, Number(rowIndex) + filterRowIndex);
                    cells[xc] = { content: cell.value.toString() };
                    if (cell.format) {
                        const formatId = getItemId(cell.format, data.formats);
                        cells[xc].format = formatId;
                    }
                }
            }
            filterRowIndex += result[0].length;
        }
        const sheet = {
            ...createEmptySheet(uuidGenerator.uuidv4(), _t("Active Filters")),
            cells,
            colNumber: numberOfCols,
            rowNumber: filterRowIndex,
        };
        data.sheets.push(sheet);
    }
}
