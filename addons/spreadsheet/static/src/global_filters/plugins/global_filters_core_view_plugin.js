/** @ts-check */

/**
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 * @typedef {import("@spreadsheet").DateGlobalFilter} DateGlobalFilter
 * @typedef {import("@spreadsheet").RelationalGlobalFilter} RelationalGlobalFilter
 * @typedef {import("@spreadsheet").DateValue} DateValue
 * @typedef {import("@spreadsheet").DateDefaultValue} DateDefaultValue
 */

import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { user } from "@web/core/user";

import { EvaluationError, helpers } from "@odoo/o-spreadsheet";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";

import {
    checkFilterValueIsValid,
    getDateDomain,
    getDateRange,
} from "@spreadsheet/global_filters/helpers";
import { OdooCoreViewPlugin } from "@spreadsheet/plugins";
import { getItemId } from "../../helpers/model";
import { serializeDate } from "@web/core/l10n/dates";
import { getFilterCellValue, getFilterValueDomain } from "../helpers";

const { DateTime } = luxon;

const { UuidGenerator, createEmptyExcelSheet, createEmptySheet, toXC, toNumber } = helpers;
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
            case "SET_GLOBAL_FILTER_VALUE":
                if (cmd.value === undefined) {
                    this._clearGlobalFilterValue(cmd.id);
                } else {
                    this._setGlobalFilterValue(cmd.id, cmd.value);
                }
                break;
            case "REMOVE_GLOBAL_FILTER":
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
        const value = this.getGlobalFilterValue(filter.id);
        const field = fieldMatching.chain;
        if (!field || !value) {
            return new Domain();
        } else if (filter.type === "date") {
            return this._getDateDomain(filter, fieldMatching);
        } else {
            return getFilterValueDomain(filter, value, field);
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
            case "date":
                return this._getDateValueFromDefaultValue(filter.defaultValue);
            case "relation":
                if (filter.defaultValue.ids === "current_user") {
                    return { ...filter.defaultValue, ids: [user.userId] };
                }
                return filter.defaultValue;
            default:
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
        const filter = this._getGlobalFilterLabel(filterName);
        if (!filter) {
            throw new EvaluationError(
                _t(`Filter "%(filter_name)s" not found`, { filter_name: filterName })
            );
        }
        switch (filter.type) {
            case "date":
                return this._getDateFilterDisplayValue(filter);
            default: {
                const value = this.getGlobalFilterValue(filter.id);
                if (!value) {
                    return [[{ value: "" }]];
                }
                return getFilterCellValue(this.getters, filter, value);
            }
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
            ...(this.getGlobalFilterValue(filterId)?.strings ?? []),
            ...(filter.defaultValue?.strings ?? []),
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
        this.values[id] = {
            preventDefaultValue: false,
            value,
        };
    }

    /**
     * Set the current value to empty values which functionally deactivate the filter
     *
     * @param {string} id Id of the filter
     */
    _clearGlobalFilterValue(id) {
        this.values[id] = {
            preventDefaultValue: true,
            value: undefined,
        };
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Get the global filter with the given name
     *
     * @param {string} label Label
     * @returns {GlobalFilter|undefined}
     */
    _getGlobalFilterLabel(label) {
        return this.getters
            .getGlobalFilters()
            .find(
                (filter) =>
                    this.getters.dynamicTranslate(filter.label) ===
                    this.getters.dynamicTranslate(label)
            );
    }

    _getDateFilterDisplayValue(filter) {
        const { from, to } = getDateRange(this.getGlobalFilterValue(filter.id));
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

    /**
     * Get the value derived from the default value of a date filter.
     * e.g. if the default value is "this_year", it returns the actual current
     * year. If it's a relative period, it returns the period as value.
     *
     * @param {DateDefaultValue} defaultValue
     * @returns {DateValue|undefined}
     */
    _getDateValueFromDefaultValue(defaultValue) {
        const year = DateTime.local().year;
        switch (defaultValue) {
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
            case "today":
            case "yesterday":
            case "last_7_days":
            case "last_30_days":
            case "last_90_days":
            case "month_to_date":
            case "last_month":
            case "last_12_months":
            case "year_to_date":
                return {
                    type: "relative",
                    period: defaultValue,
                };
        }
        return undefined;
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
        const { from, to } = getDateRange(this.getGlobalFilterValue(filter.id), offset);
        return getDateDomain(from, to, field, type);
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
