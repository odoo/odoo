/** @ts-check */

import { _t } from "@web/core/l10n/translation";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { Domain } from "@web/core/domain";
import { getOperatorLabel as getDomainOperatorLabel } from "@web/core/tree_editor/tree_editor_operator_editor";

import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";

import { Registry } from "@spreadsheet/o_spreadsheet/o_spreadsheet";
import { deepEqual } from "@web/core/utils/objects";
import { formatList } from "@web/core/l10n/utils";

export const globalFieldMatchingRegistry = new Registry();
export const globalFilterDateRegistry = new Registry();

const { DateTime, Interval } = luxon;

/**
 * @typedef {import("@spreadsheet").DateValue} DateValue
 * @typedef {import("@spreadsheet").MonthDateValue} MonthDateValue
 * @typedef {import("@spreadsheet").QuarterDateValue} QuarterDateValue
 * @typedef {import("@spreadsheet").YearDateValue} YearDateValue
 * @typedef {import("@spreadsheet").RelativeDateValue} RelativeDateValue
 * @typedef {import("@spreadsheet").DateRangeValue} DateRangeValue
 */

/**
 * @param {DateValue} dateFilterValue
 * @param {{ chain: string, type: string }} [fieldMatching]
 * @returns {string}
 */
export function getBestGranularity(dateFilterValue, fieldMatching, getters) {
    if (!dateFilterValue) {
        return "year";
    }
    const { from, to } = getDateRange(dateFilterValue, 0, DateTime.local(), getters);
    const numberOfDays = Math.round(to.diff(from, "days").days);
    if (numberOfDays <= 1) {
        return fieldMatching?.type === "datetime" ? "hour" : "day";
    } else if (numberOfDays <= 90) {
        return "day";
    } else if (numberOfDays <= 365 * 3) {
        return "month";
    } else {
        return "year";
    }
}

/**
 * @param {DateValue} dateFilterValue
 * @returns {string[]}
 */
export function getValidGranularities(dateFilterValue, getters) {
    if (!dateFilterValue) {
        return ["week", "month", "quarter", "year"];
    }
    const { from, to } = getDateRange(dateFilterValue, 0, DateTime.local(), getters);
    const numberOfDays = Math.round(to.diff(from, "days").days);
    if (numberOfDays <= 1) {
        return ["hour", "day"];
    } else if (numberOfDays <= 7) {
        return ["hour", "day", "week"];
    } else if (numberOfDays <= 31) {
        return ["hour", "day", "week", "month"];
    } else if (numberOfDays <= 31 * 3) {
        return ["day", "week", "month", "quarter"];
    } else {
        return ["week", "month", "quarter", "year"];
    }
}

export function getDateGlobalFilterRegistryItem(value) {
    const registryKey = value.type === "relative" ? value.period : value.type;
    return globalFilterDateRegistry.get(registryKey);
}

export function getDateGlobalFilterValueFromDefault(value) {
    if (!value || typeof value !== "string") {
        return undefined;
    }
    const now = DateTime.local();
    const registryItem = globalFilterDateRegistry.get(value);
    return registryItem.canOnlyBeDefault
        ? registryItem.getDefaultValue(now)
        : { type: "relative", period: value };
}

export function getDateGlobalFilterTypes() {
    return globalFilterDateRegistry
        .getKeys()
        .sort(
            (a, b) =>
                globalFilterDateRegistry.get(a).sequence - globalFilterDateRegistry.get(b).sequence
        );
}

/**
 * Compute the display name of a date filter value.
 */
export function dateFilterValueToString(value, getters) {
    if (!value || !value.type) {
        return _t("All time");
    }
    return getDateGlobalFilterRegistryItem(value).getValueString(value, getters);
}

/**
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 */

/**
 * Check if the default value is valid for a given filter.
 * @returns {boolean}
 */
export function checkFilterDefaultValueIsValid(filter, defaultValue) {
    if (defaultValue === undefined) {
        return true;
    }
    switch (filter.type) {
        case "date":
            return isDateFilterDefaultValueValid(defaultValue);
        default: {
            const { validateDefaultValue } = getFilterBehavior(filter, defaultValue.operator);
            return validateDefaultValue(defaultValue);
        }
    }
}

const SET_OPERATORS_BEHAVIORS = {
    operators: ["set", "not set"],
    validateValue: isSetValueValid,
    validateDefaultValue: isSetValueValid,
    getSearchBarFacetValues: (env, filter, filterValue) => [
        getDomainOperatorLabel(filterValue.operator),
    ],
    toDomain(fieldPath, filterValue) {
        const domainOperator = filterValue.operator === "set" ? "!=" : "=";
        return new Domain([[fieldPath, domainOperator, false]]);
    },
    toCellValue(getters, filter, filterValue) {
        return { value: filterValue.operator === "set" };
    },
};

const FILTERS_BEHAVIORS = {
    text: [
        {
            operators: ["ilike", "not ilike"],
            defaultValue: { strings: [] },
            validateValue: (filterValue) => isArrayOfStrings(filterValue.strings),
            validateDefaultValue: (filterValue) => isArrayOfStrings(filterValue.strings),
            getSearchBarFacetValues: (env, filter, filterValue) => filterValue.strings,
            toDomain(fieldPath, filterValue) {
                return Domain.or(
                    filterValue.strings.map((str) => [[fieldPath, filterValue.operator, str]])
                );
            },
            toCellValue(getters, filter, filterValue) {
                return { value: filterValue.strings.join(", ") };
            },
        },
        {
            operators: ["in", "not in"],
            defaultValue: { strings: [] },
            validateValue: (filterValue) => isArrayOfStrings(filterValue.strings),
            validateDefaultValue: (filterValue) => isArrayOfStrings(filterValue.strings),
            getSearchBarFacetValues: (env, filter, filterValue) => filterValue.strings,
            toDomain(fieldPath, filterValue) {
                return new Domain([[fieldPath, filterValue.operator, filterValue.strings]]);
            },
            toCellValue(getters, filter, filterValue) {
                return { value: filterValue.strings.join(", ") };
            },
        },
        {
            operators: ["starts with"],
            defaultValue: { strings: [] },
            validateValue: (filterValue) => isArrayOfStrings(filterValue.strings),
            validateDefaultValue: (filterValue) => isArrayOfStrings(filterValue.strings),
            getSearchBarFacetValues: (env, filter, filterValue) => filterValue.strings,
            toDomain(fieldPath, filterValue) {
                return Domain.or(
                    filterValue.strings.map((str) => [[fieldPath, "=ilike", `${str}%`]])
                );
            },
            toCellValue(getters, filter, filterValue) {
                return { value: filterValue.strings.join(", ") };
            },
        },
        SET_OPERATORS_BEHAVIORS,
    ],
    relation: [
        {
            operators: ["in", "not in", "child_of"],
            defaultValue: { ids: [] },
            validateValue: (filterValue) => isArrayOfIds(filterValue.ids),
            validateDefaultValue: isCurrentUserOrArrayOfIds,
            async getSearchBarFacetValues(env, filter, filterValue) {
                const values = await env.services.name.loadDisplayNames(
                    filter.modelName,
                    filterValue.ids
                );
                return Object.values(values).map((value) =>
                    typeof value === "string" ? value : _t("Inaccessible/missing record ID")
                );
            },
            toDomain(fieldPath, filterValue) {
                return new Domain([[fieldPath, filterValue.operator, filterValue.ids]]);
            },
            toCellValue(getters, filter, filterValue) {
                return [[{ value: filterValue.ids.join(", ") }]];
            },
        },
        {
            operators: ["ilike", "not ilike"],
            defaultValue: { strings: [] },
            validateValue: (filterValue) => isArrayOfStrings(filterValue.strings),
            validateDefaultValue: (filterValue) => isArrayOfStrings(filterValue.strings),
            getSearchBarFacetValues: (env, filter, filterValue) => filterValue.strings,
            toDomain(fieldPath, filterValue) {
                return Domain.or(
                    filterValue.strings.map((str) => [[fieldPath, filterValue.operator, str]])
                );
            },
            toCellValue(getters, filter, filterValue) {
                return { value: filterValue.strings.join(", ") };
            },
        },
        SET_OPERATORS_BEHAVIORS,
    ],
    selection: [
        {
            operators: ["in", "not in"],
            defaultValue: { selectionValues: [] },
            validateValue: (filterValue) => isArrayOfStrings(filterValue.selectionValues),
            validateDefaultValue: (filterValue) => isArrayOfStrings(filterValue.selectionValues),
            async getSearchBarFacetValues(env, filter, filterValue) {
                const fields = await env.services.field.loadFields(filter.resModel);
                const field = fields[filter.selectionField];
                if (!field) {
                    throw new Error(
                        `Field ${filter.selectionField} not found in model ${filter.resModel}`
                    );
                }
                return filterValue.selectionValues.map((value) => {
                    const option = field.selection.find((option) => option[0] === value);
                    return option ? option[1] : value;
                });
            },
            toDomain(fieldPath, filterValue) {
                return new Domain([[fieldPath, filterValue.operator, filterValue.selectionValues]]);
            },
            toCellValue(getters, filter, filterValue) {
                return { value: filterValue.selectionValues.join(", ") };
            },
        },
    ],
    boolean: [SET_OPERATORS_BEHAVIORS],
    numeric: [
        {
            operators: ["=", "!=", ">", "<"],
            defaultValue: { targetValue: undefined },
            validateValue: (filterValue) => isNumericFilterValueValid(filterValue.targetValue),
            validateDefaultValue: (filterValue) =>
                isNumericFilterValueValid(filterValue.targetValue),
            getSearchBarFacetValues: (env, filter, filterValue) => {
                if (filterValue.targetValue === undefined) {
                    return [];
                }
                return [`${filterValue.targetValue}`];
            },
            toDomain(fieldPath, filterValue) {
                return new Domain([[fieldPath, filterValue.operator, filterValue.targetValue]]);
            },
            toCellValue(getters, filter, filterValue) {
                return {
                    value: filterValue.targetValue !== undefined ? filterValue.targetValue : "",
                };
            },
        },
        {
            operators: ["between"],
            defaultValue: { minimumValue: undefined, maximumValue: undefined },
            validateValue: (filterValue) =>
                isNumericFilterValueValid(filterValue.minimumValue) &&
                isNumericFilterValueValid(filterValue.maximumValue),
            validateDefaultValue: (filterValue) =>
                isNumericFilterValueValid(filterValue.minimumValue) &&
                isNumericFilterValueValid(filterValue.maximumValue),
            getSearchBarFacetValues: (env, filter, filterValue) => {
                if (
                    filterValue.minimumValue === undefined &&
                    filterValue.maximumValue === undefined
                ) {
                    return [];
                }
                return [formatList([filterValue.minimumValue, filterValue.maximumValue])];
            },
            toDomain(fieldPath, filterValue) {
                return new Domain([
                    [fieldPath, ">=", filterValue.minimumValue],
                    [fieldPath, "<=", filterValue.maximumValue],
                ]);
            },
            toCellValue(getters, filter, filterValue) {
                return [
                    [{ value: filterValue.minimumValue }],
                    [{ value: filterValue.maximumValue }],
                ];
            },
        },
    ],
};

/**
 * Check if the value is valid for given filter.
 * @param {GlobalFilter | CmdGlobalFilter} filter
 * @param {any} value
 * @returns {boolean}
 */
export function checkFilterValueIsValid(filter, value) {
    if (value === undefined) {
        return true;
    }
    switch (filter.type) {
        case "date":
            return isDateFilterValueValid(value);
        default: {
            const { validateValue } = getFilterBehavior(filter, value.operator);
            return validateValue(value);
        }
    }
}

function isArrayOfStrings(strings) {
    return (
        Array.isArray(strings) &&
        strings.length &&
        strings.every((item) => typeof item === "string")
    );
}

/**
 * A numeric filter value is valid if it is a number
 * @returns {boolean}
 */
function isNumericFilterValueValid(value) {
    return typeof value === "number";
}

function isArrayOfIds(ids) {
    return Array.isArray(ids) && ids.length && ids.every((id) => Number.isInteger(id));
}

function isCurrentUserOrArrayOfIds(value) {
    return value.ids === "current_user" || isArrayOfIds(value.ids);
}

/**
 * A boolean filter value is valid if it is an array of booleans. It's the same
 * for the default value.
 * @returns {boolean}
 */
function isSetValueValid(value) {
    return value.operator === "set" || value.operator === "not set";
}

/**
 * A date filter default value is valid if it's a known string representing
 * a relative period (like "last_7_days") or a "current" period (like "this_month", "this_quarter", "this_year"),
 * @returns {boolean}
 */
function isDateFilterDefaultValueValid(value) {
    return globalFilterDateRegistry.contains(value);
}

/**
 * A date filter value is valid depending on its type:
 * - "relative": must have a valid period (like "last_7_days")
 * - "month": must have a valid year and month
 * - "quarter": must have a valid year and quarter
 * - "year": must have a valid year
 * - "range": must have valid from and to values (or be empty)
 * @returns {boolean}
 */
function isDateFilterValueValid(value) {
    try {
        return getDateGlobalFilterRegistryItem(value).isValueValid(value);
    } catch {
        return false;
    }
}

/**
 *
 * @param {Record<string, FieldMatching>} fieldMatchings
 */
export function checkFilterFieldMatching(fieldMatchings) {
    for (const fieldMatch of Object.values(fieldMatchings)) {
        if (fieldMatch.offset && (!fieldMatch.chain || !fieldMatch.type)) {
            return CommandResult.InvalidFieldMatch;
        }
    }

    return CommandResult.Success;
}

globalFilterDateRegistry
    .add("today", {
        sequence: 10,
        label: _t("Today"),
        getDateRange: (now, value, offset) => getRelativeDateFromTo(now, offset, "today"),
        getNextDateFilterValue: () => getNextValueForRelativeDatePeriod("today"),
        getPreviousDateFilterValue: () => getPreviousValueForRelativeDatePeriod("today"),
        isValueValid: (value) => true,
        getValueString: (value) => _t("Today"),
        isFixedPeriod: false,
        category: "day",
    })
    .add("yesterday", {
        sequence: 20,
        label: _t("Yesterday"),
        getDateRange: (now, value, offset) => getRelativeDateFromTo(now, offset, "yesterday"),
        getNextDateFilterValue: () => getNextValueForRelativeDatePeriod("yesterday"),
        getPreviousDateFilterValue: () => getPreviousValueForRelativeDatePeriod("yesterday"),
        isValueValid: (value) => true,
        getValueString: (value) => _t("Yesterday"),
        isFixedPeriod: false,
        category: "day",
    })
    .add("last_7_days", {
        sequence: 30,
        label: _t("Last 7 Days"),
        getDateRange: (now, value, offset) => getRelativeDateFromTo(now, offset, "last_7_days"),
        getNextDateFilterValue: () => getNextValueForRelativeDatePeriod("last_7_days"),
        getPreviousDateFilterValue: () => getPreviousValueForRelativeDatePeriod("last_7_days"),
        isValueValid: (value) => true,
        getValueString: (value) => _t("Last 7 Days"),
        isFixedPeriod: false,
        category: "last_period",
    })
    .add("last_30_days", {
        sequence: 40,
        label: _t("Last 30 Days"),
        getDateRange: (now, value, offset) => getRelativeDateFromTo(now, offset, "last_30_days"),
        getNextDateFilterValue: () => getNextValueForRelativeDatePeriod("last_30_days"),
        getPreviousDateFilterValue: () => getPreviousValueForRelativeDatePeriod("last_30_days"),
        isValueValid: (value) => true,
        getValueString: (value) => _t("Last 30 Days"),
        isFixedPeriod: false,
        category: "last_period",
    })
    .add("last_90_days", {
        sequence: 50,
        label: _t("Last 90 Days"),
        getDateRange: (now, value, offset) => getRelativeDateFromTo(now, offset, "last_90_days"),
        getNextDateFilterValue: () => getNextValueForRelativeDatePeriod("last_90_days"),
        getPreviousDateFilterValue: () => getPreviousValueForRelativeDatePeriod("last_90_days"),
        isValueValid: (value) => true,
        getValueString: (value) => _t("Last 90 Days"),
        isFixedPeriod: false,
        category: "last_period",
    })
    .add("month_to_date", {
        sequence: 60,
        label: _t("Month to Date"),
        getDateRange: (now, value, offset) => getRelativeDateFromTo(now, offset, "month_to_date"),
        getNextDateFilterValue: () => getNextValueForRelativeDatePeriod("month_to_date"),
        getPreviousDateFilterValue: () => getPreviousValueForRelativeDatePeriod("month_to_date"),
        isValueValid: (value) => true,
        getValueString: (value) => _t("Month to Date"),
        isFixedPeriod: false,
        category: "month",
    })
    .add("last_month", {
        sequence: 70,
        label: _t("Last Month"),
        getDateRange: (now, value, offset) => getRelativeDateFromTo(now, offset, "last_month"),
        getNextDateFilterValue: () => getNextValueForRelativeDatePeriod("last_month"),
        getPreviousDateFilterValue: () => getPreviousValueForRelativeDatePeriod("last_month"),
        isValueValid: (value) => true,
        getValueString: (value) => _t("Last Month"),
        isFixedPeriod: false,
        category: "month",
    })
    .add("this_month", {
        sequence: 80,
        label: _t("Current Month"),
        canOnlyBeDefault: true,
        getDefaultValue: (now) => ({ type: "month", year: now.year, month: now.month }),
        category: "month",
    })
    .add("month", {
        sequence: 90,
        label: _t("Month"),
        getDateRange: (now, value, offset) => getFixedPeriodFromTo(now, offset, value),
        getNextDateFilterValue: (value) => getNextFixedDateFilterValue(value),
        getPreviousDateFilterValue: (value) => getPreviousFixedDateFilterValue(value),
        isValueValid: (value) =>
            typeof value.year === "number" &&
            typeof value.month === "number" &&
            value.month >= 1 &&
            value.month <= 12,
        getValueString: (value) =>
            DateTime.local().set({ year: value.year, month: value.month }).toFormat("LLLL yyyy"),
        isFixedPeriod: true,
        getCurrentFixedPeriod: (now) => ({ type: "month", year: now.year, month: now.month }),
        category: "month",
    })
    .add("this_quarter", {
        sequence: 100,
        label: _t("Current Quarter"),
        canOnlyBeDefault: true,
        getDefaultValue: (now) => ({
            type: "quarter",
            year: now.year,
            quarter: Math.floor((now.month - 1) / 3) + 1,
        }),
        category: "month",
    })
    .add("quarter", {
        sequence: 110,
        label: _t("Quarter"),
        getDateRange: (now, value, offset) => getFixedPeriodFromTo(now, offset, value),
        getNextDateFilterValue: (value) => getNextFixedDateFilterValue(value),
        getPreviousDateFilterValue: (value) => getPreviousFixedDateFilterValue(value),
        isValueValid: (value) =>
            typeof value.year === "number" &&
            typeof value.quarter === "number" &&
            value.quarter >= 1 &&
            value.quarter <= 4,
        getValueString: (value) =>
            _t("Q%(quarter)s %(year)s", { quarter: value.quarter, year: value.year }),
        isFixedPeriod: true,
        getCurrentFixedPeriod: (now) => ({
            type: "quarter",
            year: now.year,
            quarter: Math.floor((now.month - 1) / 3) + 1,
        }),
        category: "month",
    })
    .add("year_to_date", {
        sequence: 120,
        label: _t("Year to Date"),
        getDateRange: (now, value, offset) => getRelativeDateFromTo(now, offset, "year_to_date"),
        getNextDateFilterValue: () => getNextValueForRelativeDatePeriod("year_to_date"),
        getPreviousDateFilterValue: () => getPreviousValueForRelativeDatePeriod("year_to_date"),
        isValueValid: (value) => true,
        getValueString: (value) => _t("Year to Date"),
        isFixedPeriod: false,
        category: "year",
    })
    .add("last_12_months", {
        sequence: 130,
        label: _t("Last 12 Months"),
        getDateRange: (now, value, offset) => getRelativeDateFromTo(now, offset, "last_12_months"),
        getNextDateFilterValue: () => getNextValueForRelativeDatePeriod("last_12_months"),
        getPreviousDateFilterValue: () => getPreviousValueForRelativeDatePeriod("last_12_months"),
        isValueValid: (value) => true,
        getValueString: (value) => _t("Last 12 Months"),
        isFixedPeriod: false,
        category: "year",
    })
    .add("this_year", {
        sequence: 140,
        label: _t("Current Year"),
        canOnlyBeDefault: true,
        getDefaultValue: (now) => ({ type: "year", year: now.year }),
        category: "year",
    })
    .add("year", {
        sequence: 150,
        label: _t("Year"),
        getDateRange: (now, value, offset) => getFixedPeriodFromTo(now, offset, value),
        getNextDateFilterValue: (value) => getNextFixedDateFilterValue(value),
        getPreviousDateFilterValue: (value) => getPreviousFixedDateFilterValue(value),
        isValueValid: (value) => typeof value.year === "number",
        getValueString: (value) => String(value.year),
        isFixedPeriod: true,
        getCurrentFixedPeriod: (now) => ({ type: "year", year: now.year }),
        category: "year",
    })
    .add("range", {
        sequence: 160,
        label: _t("Custom Range"),
        getDateRange: (now, value, offset) => ({
            from: value.from && DateTime.fromISO(value.from).startOf("day"),
            to: value.to && DateTime.fromISO(value.to).endOf("day"),
        }),
        getNextDateFilterValue: (value) => getNextRangeDateFilterValue(value),
        getPreviousDateFilterValue: (value) => getPreviousRangeDateFilterValue(value),
        isValueValid: (value) =>
            (value.from === undefined || typeof value.from === "string") &&
            (value.to === undefined || typeof value.to === "string"),
        getValueString: (value) => {
            if (value.from && value.to) {
                const interval = Interval.fromDateTimes(
                    DateTime.fromISO(value.from).startOf("day"),
                    DateTime.fromISO(value.to).endOf("day")
                );
                return interval.toLocaleString(DateTime.DATE_FULL);
            } else if (value.from) {
                return _t("Since %(from)s", {
                    from: DateTime.fromISO(value.from).toLocaleString(DateTime.DATE_FULL),
                });
            } else if (value.to) {
                return _t("Until %(to)s", {
                    to: DateTime.fromISO(value.to).toLocaleString(DateTime.DATE_FULL),
                });
            }
            return _t("All time");
        },
        isFixedPeriod: true,
        getCurrentFixedPeriod: () => ({ from: "", to: "", type: "range" }),
        category: "misc",
    });

/**
 * The from-to date range from a date filter value.
 *
 * @returns {{ from?: DateTime, to?: DateTime }}
 */
export function getDateRange(value, offset = 0, now = DateTime.local(), getters) {
    if (!value) {
        return {};
    }
    return getDateGlobalFilterRegistryItem(value).getDateRange(now, value, offset, getters);
}

function getFixedPeriodFromTo(now, offset, value) {
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

function getRelativeDateFromTo(now, offset, period) {
    const startOfNextDay = now.plus({ days: 1 }).startOf("day");
    let to = now.endOf("day");
    let from = to;
    switch (period) {
        case "today": {
            const offsetParam = { days: offset };
            from = now.startOf("day").plus(offsetParam);
            to = now.endOf("day").plus(offsetParam);
            break;
        }
        case "yesterday": {
            const offsetParam = { days: offset };
            from = now.startOf("day").minus({ days: 1 }).plus(offsetParam);
            to = now.endOf("day").minus({ days: 1 }).plus(offsetParam);
            break;
        }
        case "month_to_date": {
            const offsetParam = { months: offset };
            from = now.startOf("month").plus(offsetParam);
            to = now.endOf("day").plus(offsetParam);
            break;
        }
        case "last_month": {
            const offsetParam = { months: offset };
            from = now.plus(offsetParam).minus({ months: 1 }).startOf("month");
            to = now.plus(offsetParam).minus({ months: 1 }).endOf("month");
            break;
        }
        case "year_to_date": {
            const offsetParam = { years: offset };
            from = now.startOf("year").plus(offsetParam);
            to = now.endOf("day").plus(offsetParam);
            break;
        }
        case "last_7_days": {
            const offsetParam = { days: 7 * offset };
            to = to.plus(offsetParam);
            from = startOfNextDay.minus({ days: 7 }).plus(offsetParam);
            break;
        }
        case "last_30_days": {
            const offsetParam = { days: 30 * offset };
            to = to.plus(offsetParam);
            from = startOfNextDay.minus({ days: 30 }).plus(offsetParam);
            break;
        }
        case "last_90_days": {
            const offsetParam = { days: 90 * offset };
            to = to.plus(offsetParam);
            from = startOfNextDay.minus({ days: 90 }).plus(offsetParam);
            break;
        }
        case "last_12_months": {
            const offsetParam = { months: 12 * offset };
            to = startOfNextDay.minus({ months: 1 }).endOf("month").plus(offsetParam);
            from = startOfNextDay.minus({ months: 12 }).startOf("month").plus(offsetParam);
            break;
        }
        default:
            return undefined;
    }
    return { from, to };
}

function getNextFixedDateFilterValue(value) {
    switch (value?.type) {
        case "quarter":
            return {
                type: "quarter",
                year: value.quarter === 4 ? value.year + 1 : value.year,
                quarter: value.quarter === 4 ? 1 : value.quarter + 1,
            };
        case "month":
            return {
                type: "month",
                year: value.month === 12 ? value.year + 1 : value.year,
                month: value.month === 12 ? 1 : value.month + 1,
            };
        case "year":
            return {
                type: "year",
                year: value.year + 1,
            };
    }
    return undefined;
}

/**
 * Compute the next date filter value.
 *
 * @param {DateValue | undefined} value
 * @returns {DateValue | undefined}
 */
export function getNextDateFilterValue(value) {
    if (!value) {
        return undefined;
    }
    return getDateGlobalFilterRegistryItem(value).getNextDateFilterValue(value);
}

function getPreviousFixedDateFilterValue(value) {
    switch (value?.type) {
        case "quarter":
            return {
                type: "quarter",
                year: value.quarter === 1 ? value.year - 1 : value.year,
                quarter: value.quarter === 1 ? 4 : value.quarter - 1,
            };
        case "month":
            return {
                type: "month",
                year: value.month === 1 ? value.year - 1 : value.year,
                month: value.month === 1 ? 12 : value.month - 1,
            };
        case "year":
            return {
                type: "year",
                year: value.year - 1,
            };
    }
    return undefined;
}

export function getPreviousDateFilterValue(value) {
    if (!value) {
        return undefined;
    }
    return getDateGlobalFilterRegistryItem(value).getPreviousDateFilterValue(value);
}

/**
 * Compute the next value for the given relative period.
 *
 * @param {RelativeDateValue.period} period
 * @returns {DateValue}
 */
function getNextValueForRelativeDatePeriod(period) {
    switch (period) {
        case "today":
        case "yesterday":
        case "last_7_days":
        case "last_30_days":
        case "last_90_days": {
            const { from, to } = getRelativeDateFromTo(DateTime.local(), 1, period);
            return {
                type: "range",
                from: from.toISODate(),
                to: to.toISODate(),
            };
        }
        case "last_12_months": {
            const { from, to } = getRelativeDateFromTo(DateTime.local(), 1, period);
            return {
                type: "range",
                from: from.startOf("month").toISODate(),
                to: to.endOf("month").toISODate(),
            };
        }
        case "last_month": {
            const now = DateTime.local();
            return {
                type: "month",
                year: now.year,
                month: now.month,
            };
        }
        case "month_to_date": {
            const now = DateTime.local().plus({ months: 1 });
            return {
                type: "month",
                year: now.year,
                month: now.month,
            };
        }
        case "year_to_date": {
            return {
                type: "year",
                year: DateTime.local().year + 1,
            };
        }
    }
}

/**
 * Compute the previous value for the given relative period.
 *
 * @param {RelativeDateValue.period} period
 * @returns {DateValue}
 */
function getPreviousValueForRelativeDatePeriod(period) {
    switch (period) {
        case "today":
        case "yesterday":
        case "last_7_days":
        case "last_30_days":
        case "last_90_days": {
            const { from, to } = getRelativeDateFromTo(DateTime.local(), -1, period);
            return {
                type: "range",
                from: from.toISODate(),
                to: to.toISODate(),
            };
        }
        case "last_12_months": {
            const { from, to } = getRelativeDateFromTo(DateTime.local(), -1, period);
            return {
                type: "range",
                from: from.startOf("month").toISODate(),
                to: to.endOf("month").toISODate(),
            };
        }

        case "last_month": {
            const now = DateTime.local().minus({ months: 2 });
            return {
                type: "month",
                year: now.year,
                month: now.month,
            };
        }
        case "month_to_date": {
            const now = DateTime.local().minus({ months: 1 });
            return {
                type: "month",
                year: now.year,
                month: now.month,
            };
        }
        case "year_to_date": {
            return {
                type: "year",
                year: DateTime.local().year - 1,
            };
        }
    }
}

/**
 * Compute the next date range filter value.
 *
 * @param {DateRangeValue} value
 * @returns {DateRangeValue}
 */
function getNextRangeDateFilterValue(value) {
    if (!value.from && !value.to) {
        return value;
    }
    const from = DateTime.fromISO(value.from);
    const to = DateTime.fromISO(value.to);
    const days = to.diff(from, "days").days + 1; // +1 to include the end date
    return {
        type: "range",
        from: from.plus({ days }).toISODate(),
        to: to.plus({ days }).toISODate(),
    };
}

/**
 * Compute the previous date range filter value.
 *
 * @param {DateRangeValue} value
 * @returns {DateRangeValue}
 */
function getPreviousRangeDateFilterValue(value) {
    if (!value.from && !value.to) {
        return value;
    }
    const from = DateTime.fromISO(value.from);
    const to = DateTime.fromISO(value.to);
    const days = to.diff(from, "days").days + 1; // +1 to include the end date
    return {
        type: "range",
        from: from.minus({ days }).toISODate(),
        to: to.minus({ days }).toISODate(),
    };
}

export function getDateDomain(from, to, field, fieldType) {
    const serialize = fieldType === "date" ? serializeDate : serializeDateTime;
    if (from && to) {
        return new Domain(["&", [field, ">=", serialize(from)], [field, "<=", serialize(to)]]);
    }
    if (from) {
        return new Domain([[field, ">=", serialize(from)]]);
    }
    if (to) {
        return new Domain([[field, "<=", serialize(to)]]);
    }
    return new Domain();
}

const TEXT_OPERATORS = ["ilike", "not ilike", "starts with"];

export function getFilterTypeOperators(filterType) {
    if (filterType === "date") {
        return [];
    }
    return FILTERS_BEHAVIORS[filterType].flatMap((entry) => entry.operators);
}

export function isTextualOperator(operator) {
    return TEXT_OPERATORS.includes(operator);
}

export function isSetOperator(operator) {
    return SET_OPERATORS_BEHAVIORS.operators.includes(operator);
}

export function getDefaultValue(type) {
    if (type === "date" || type === "boolean") {
        return undefined;
    }
    const defaultOperator = FILTERS_BEHAVIORS[type][0].operators[0];
    return {
        operator: defaultOperator,
        ...getEmptyFilterValue({ type }, defaultOperator),
    };
}

function getFilterBehavior(filter, operator) {
    const entry = FILTERS_BEHAVIORS[filter.type].find((entry) =>
        entry.operators.includes(operator)
    );
    if (!entry) {
        throw new Error(
            `No behavior found for filter type "${filter.type}" and operator "${operator}"`
        );
    }
    return entry;
}

export function getFilterValueDomain(filter, filterValue, fieldPath) {
    return getFilterBehavior(filter, filterValue.operator).toDomain(fieldPath, filterValue);
}

export function getEmptyFilterValue(filter, operator) {
    if (filter.type === "date") {
        return undefined;
    }
    return getFilterBehavior(filter, operator).defaultValue;
}

export function isEmptyFilterValue(filter, filterValue) {
    if (!filterValue) {
        return true;
    }
    const emptyValue = getEmptyFilterValue(filter, filterValue.operator);
    if (!emptyValue) {
        return false;
    }
    for (const key in emptyValue) {
        if (!deepEqual(emptyValue[key], filterValue[key])) {
            return false;
        }
    }
    return true;
}

export function getFilterCellValue(getters, filter, filterValue) {
    return getFilterBehavior(filter, filterValue.operator).toCellValue(
        getters,
        filter,
        filterValue
    );
}

export async function getFacetInfo(env, filter, filterValue, getters) {
    let values;
    const separator = _t("or");
    switch (filter.type) {
        case "date": {
            if (!filterValue) {
                throw new Error("Should be defined at this point");
            }
            values = [dateFilterValueToString(filterValue, getters)];
            break;
        }
        default: {
            values = await getFilterBehavior(filter, filterValue.operator).getSearchBarFacetValues(
                env,
                filter,
                filterValue
            );
            break;
        }
    }
    return {
        title: filter.label,
        values,
        id: filter.id,
        separator,
        operator: getOperatorLabel(filterValue.operator),
    };
}

function getOperatorLabel(operator) {
    if (!operator) {
        return "";
    }
    switch (operator) {
        case "=":
        case "in":
        case "set":
        case "not set":
            return "";
        case "!=":
        case "not in":
            return _t("not");
    }
    return getDomainOperatorLabel(operator);
}
