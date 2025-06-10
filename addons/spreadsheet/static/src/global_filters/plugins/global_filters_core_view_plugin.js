/** @ts-check */

/**
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 * @typedef {import("@spreadsheet").DateGlobalFilter} DateGlobalFilter
 * @typedef {import("@spreadsheet").RelationalGlobalFilter} RelationalGlobalFilter
 */

import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { user } from "@web/core/user";

import { EvaluationError, helpers } from "@odoo/o-spreadsheet";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";

import {
    checkFilterValueIsValid,
    getDateDomain,
    getRelativeDateFromTo,
} from "@spreadsheet/global_filters/helpers";
import { OdooCoreViewPlugin } from "@spreadsheet/plugins";
import { getItemId } from "../../helpers/model";
import { serializeDate } from "@web/core/l10n/dates";

const { DateTime } = luxon;

const { UuidGenerator, createEmptyExcelSheet, createEmptySheet, toXC, toNumber, toBoolean } =
    helpers;
const uuidGenerator = new UuidGenerator();

export class GlobalFiltersCoreViewPlugin extends OdooCoreViewPlugin {
    static getters = /** @type {const} */ ([
        "exportSheetWithActiveFilters",
        "getFilterDisplayValue",
        "getGlobalFilterDomain",
        "getGlobalFilterValue",
        "getActiveFilterCount",
        "isGlobalFilterActive",
        "getTextFilterOptions",
        "getTextFilterOptionsFromRanges",
    ]);
    constructor(config) {
        super(config);
        this.nameService = config.custom.env?.services.name;
        this.odooDataProvider = config.custom.odooDataProvider;
        /**
         * Cache record display names for relation filters.
         * For each filter, contains a promise resolving to
         * the list of display names.
         */
        this.recordsDisplayName = {};
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
                this.recordsDisplayName[cmd.filter.id] = cmd.filter.defaultValueDisplayNames;
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
                this.recordsDisplayName[id] = filter.defaultValueDisplayNames;
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
            case "REMOVE_GLOBAL_FILTER":
                delete this.recordsDisplayName[cmd.id];
                delete this.values[cmd.id];
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
            case "boolean":
                return this._getBooleanDomain(filter, fieldMatching);
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
        if (value !== undefined) {
            return value;
        }
        const preventDefaultValue = this.values[filterId]?.preventDefaultValue;
        if (preventDefaultValue || filter.defaultValue === undefined) {
            return undefined;
        }
        switch (filter.type) {
            case "text":
            case "boolean":
                return filter.defaultValue;
            case "date":
                if (filter.rangeType === "fixedPeriod") {
                    return this._getValueOfCurrentPeriod(filterId);
                }
                if (filter.rangeType === "relative") {
                    return filter.defaultValue;
                }
                throw new Error("from_to should not have a default value");
            case "relation":
                if (filter.defaultValue === "current_user") {
                    return [user.userId];
                }
                return filter.defaultValue;
        }
    }

    /**
     * @param {string} id Id of the filter
     *
     * @returns { boolean } true if the given filter is active
     */
    isGlobalFilterActive(id) {
        return this.getGlobalFilterValue(id) !== undefined;
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
            throw new EvaluationError(
                _t(`Filter "%(filter_name)s" not found`, { filter_name: filterName })
            );
        }
        const value = this.getGlobalFilterValue(filter.id);
        switch (filter.type) {
            case "text":
            case "boolean":
                return [[{ value: value?.length ? value.join(", ") : "" }]];
            case "date":
                return this._getDateFilterDisplayValue(filter);
            case "relation":
                return this._getRelationFilterDisplayValue(filter, value);
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
        if (filter.type !== "text" || !filter.rangesOfAllowedValues) {
            return [];
        }
        const additionOptions = [
            // add the current value because it might not be in the range
            // if the range cells changed in the meantime
            ...(this.getGlobalFilterValue(filterId) ?? []),
            ...(filter.defaultValue ?? []),
        ];
        const options = this.getTextFilterOptionsFromRanges(
            filter.rangesOfAllowedValues,
            additionOptions
        );
        return options;
    }

    /**
     * Returns the possible values a text global filter can take from a range
     * or any addition raw string value. Removes duplicates and empty string values.
     * @param {object[]} ranges
     * @param {string[]} additionalOptionValues
     */
    getTextFilterOptionsFromRanges(ranges, additionalOptionValues = []) {
        const cells = ranges.flatMap((range) =>
            this.getters.getEvaluatedCellsInZone(range.sheetId, range.zone)
        );
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
            preventDefaultValue: false,
            value,
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
        const year = DateTime.local().year;
        switch (filter.defaultValue) {
            case "this_year":
                return { type: "year", year };
            case "this_month": {
                const month = DateTime.local().month;
                return { type: "month", year, month };
            }
            case "this_quarter": {
                const quarter = Math.floor(new Date().getMonth() / 3) + 1;
                return { type: "quarter", year, quarter };
            }
        }
        throw new Error(
            "Unsupported default value for fixed period date filter: " + filter.defaultValue
        );
    }

    /**
     * Set the current value to empty values which functionally deactivate the filter
     *
     * @param {string} id Id of the filter
     */
    _clearGlobalFilterValue(id) {
        const filter = this.getters.getGlobalFilter(id);
        this.values[id] = {
            preventDefaultValue: true,
            value: undefined,
            rangeType: filter.type === "date" ? filter.rangeType : undefined,
        };
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    _getDateFilterDisplayValue(filter) {
        const { from, to } = this._getDateRange(filter);
        const locale = this.getters.getLocale();
        const _from = {
            value: from ? toNumber(serializeDate(from), locale) : "",
            format: locale.dateFormat,
        };
        const _to = {
            value: to ? toNumber(serializeDate(to), locale) : "",
            format: locale.dateFormat,
        };
        return [[_from], [_to]];
    }

    _getRelationFilterDisplayValue(filter, value) {
        if (!value?.length || !this.nameService) {
            return [[{ value: "" }]];
        }
        if (!this.recordsDisplayName[filter.id]) {
            const promise = this.nameService
                .loadDisplayNames(filter.modelName, value)
                .then((result) => {
                    this.recordsDisplayName[filter.id] = Object.values(result);
                });
            this.odooDataProvider.notifyWhenPromiseResolves(promise);
            return [[{ value: "" }]];
        }
        return [[{ value: this.recordsDisplayName[filter.id].join(", ") }]];
    }

    /**
     * @returns {{ from?: DateTime, to?: DateTime }}
     */
    _getDateRange(filter, offset = 0) {
        const value = this.getGlobalFilterValue(filter.id);
        if (!value) {
            return {};
        }
        const now = DateTime.local();

        if (filter.rangeType === "from_to") {
            const from = value.from && DateTime.fromISO(value.from).startOf("day");
            const to = value.to && DateTime.fromISO(value.to).endOf("day");
            return { from, to };
        }
        if (filter.rangeType === "relative") {
            return getRelativeDateFromTo(now, offset, value);
        }
        return this._getFixedPeriodFromTo(now, offset, value);
    }

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
        if (!fieldMatching.chain) {
            return new Domain();
        }
        const field = fieldMatching.chain;
        const type = /** @type {"date" | "datetime"} */ (fieldMatching.type);
        const offset = fieldMatching.offset || 0;
        const { from, to } = this._getDateRange(filter, offset);
        return getDateDomain(from, to, field, type);
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
        if (!value || !value.length || !fieldMatching.chain) {
            return new Domain();
        }
        const field = fieldMatching.chain;
        return Domain.or(value.map((text) => [[field, "ilike", text]]));
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

    _getBooleanDomain(filter, fieldMatching) {
        const value = this.getGlobalFilterValue(filter.id);
        if (!value || !value.length || !fieldMatching.chain) {
            return new Domain();
        }
        const field = fieldMatching.chain;
        if (value.length === 1) {
            return new Domain([[field, "=", toBoolean(value[0])]]);
        }
        return new Domain([[field, "in", [toBoolean(value[0]), toBoolean(value[1])]]]);
    }

    _getFixedPeriodFromTo(now, offset, value) {
        let granularity = "year";
        const noYear = value.year === undefined;
        if (noYear) {
            return {};
        }
        const setParam = { year: value.year };
        const plusParam = {};
        switch (value.type) {
            case "year":
                plusParam.year = offset;
                break;
            case "month":
                if (value.month !== undefined) {
                    granularity = "month";
                    setParam.month = value.month;
                    plusParam.month = offset;
                }
                break;
            case "quarter":
                if (value.quarter !== undefined) {
                    granularity = "quarter";
                    setParam.quarter = value.quarter;
                    plusParam.quarter = offset;
                }
                break;
        }
        if ("quarter" in setParam) {
            // Luxon does not consider quarter key in setParam (like moment did)
            setParam.month = setParam.quarter * 3 - 2; // start of the quarter
            delete setParam.quarter;
        }
        const date = now.set(setParam).plus(plusParam || {});
        return {
            from: date.startOf(granularity),
            to: date.endOf(granularity),
        };
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
            ...createEmptyExcelSheet(uuidGenerator.smallUuid(), _t("Active Filters")),
            ...data.sheets.at(-1),
        };
    }

    exportSheetWithActiveFilters(data) {
        if (this.getters.getGlobalFilters().length === 0) {
            return;
        }

        const cells = {
            A1: "Filter",
            B1: "Value",
        };
        const formats = {};
        let numberOfCols = 2; // at least 2 cols (filter title and filter value)
        let filterRowIndex = 1; // first row is the column titles
        for (const filter of this.getters.getGlobalFilters()) {
            cells[`A${filterRowIndex + 1}`] = filter.label;
            const result = this.getFilterDisplayValue(filter.label);
            for (const colIndex in result) {
                numberOfCols = Math.max(numberOfCols, Number(colIndex) + 2);
                for (const rowIndex in result[colIndex]) {
                    const cell = result[colIndex][rowIndex];
                    if (cell.value === undefined) {
                        continue;
                    }
                    const xc = toXC(Number(colIndex) + 1, Number(rowIndex) + filterRowIndex);
                    cells[xc] = cell.value.toString();
                    if (cell.format) {
                        const formatId = getItemId(cell.format, data.formats);
                        formats[xc] = formatId;
                    }
                }
            }
            filterRowIndex += result[0].length;
        }
        const styleId = getItemId({ bold: true }, data.styles);

        const sheet = {
            ...createEmptySheet(uuidGenerator.smallUuid(), _t("Active Filters")),
            cells,
            formats,
            styles: {
                A1: styleId,
                B1: styleId,
            },
            colNumber: numberOfCols,
            rowNumber: filterRowIndex,
        };
        data.sheets.push(sheet);
    }
}
