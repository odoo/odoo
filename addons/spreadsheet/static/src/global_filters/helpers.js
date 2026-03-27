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

const { DateTime, Interval } = luxon;

/**
 * @typedef {import("@spreadsheet").DateValue} DateValue
 * @typedef {import("@spreadsheet").MonthDateValue} MonthDateValue
 * @typedef {import("@spreadsheet").QuarterDateValue} QuarterDateValue
 * @typedef {import("@spreadsheet").YearDateValue} YearDateValue
 * @typedef {import("@spreadsheet").RelativeDateValue} RelativeDateValue
 * @typedef {import("@spreadsheet").DateRangeValue} DateRangeValue
 */

export const RELATIVE_PERIODS = {
    today: _t("Today"),
    yesterday: _t("Yesterday"),
    last_7_days: _t("Last 7 Days"),
    last_30_days: _t("Last 30 Days"),
    last_90_days: _t("Last 90 Days"),
    month_to_date: _t("Month to Date"),
    last_month: _t("Last Month"),
    last_12_months: _t("Last 12 Months"),
    year_to_date: _t("Year to Date"),
};

/**
 * @param {DateValue} dateFilterValue
 * @param {{ chain: string, type: string }} [fieldMatching]
 * @returns {string}
 */
export function getBestGranularity(dateFilterValue, fieldMatching) {
    if (!dateFilterValue) {
        return "year";
    }
    const { from, to } = getDateRange(dateFilterValue);
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
export function getValidGranularities(dateFilterValue) {
    if (!dateFilterValue) {
        return ["day", "week", "month", "quarter", "year"];
    }
    const { from, to } = getDateRange(dateFilterValue);
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

/**
 * Compute the display name of a date filter value.
 */
export function dateFilterValueToString(value) {
    switch (value?.type) {
        case "relative":
            return RELATIVE_PERIODS[value.period];
        case "month": {
            const month = DateTime.local().set({
                year: value.year,
                month: value.month,
            });
            return month.toFormat("LLLL yyyy");
        }
        case "quarter": {
            return _t("Q%(quarter)s %(year)s", {
                quarter: value.quarter,
                year: value.year,
            });
        }
        case "year":
            return String(value.year);
        case "range":
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
    }
    return _t("All time");
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
        return [[{ value: filterValue.operator === "set" }]];
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
                return [[{ value: filterValue.strings.join(", ") }]];
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
                return [[{ value: filterValue.strings.join(", ") }]];
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
                return [[{ value: filterValue.strings.join(", ") }]];
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
                return [[{ value: filterValue.strings.join(", ") }]];
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
                return [[{ value: filterValue.selectionValues.join(", ") }]];
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
                const value = filterValue.targetValue !== undefined ? filterValue.targetValue : "";
                return [[{ value }]];
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
    return (
        Object.keys(RELATIVE_PERIODS).includes(value) ||
        ["this_month", "this_quarter", "this_year"].includes(value)
    );
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
    switch (value.type) {
        case "relative":
            return Object.keys(RELATIVE_PERIODS).includes(value.period);
        case "month":
            return (
                typeof value.year === "number" &&
                typeof value.month === "number" &&
                value.month >= 1 &&
                value.month <= 12
            );
        case "quarter":
            return (
                typeof value.year === "number" &&
                typeof value.quarter === "number" &&
                value.quarter >= 1 &&
                value.quarter <= 4
            );
        case "year":
            return typeof value.year === "number";
        case "range":
            return (
                (value.from === undefined || typeof value.from === "string") &&
                (value.to === undefined || typeof value.to === "string")
            );
    }
    return false;
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

/**
 * The from-to date range from a date filter value.
 *
 * @returns {{ from?: DateTime, to?: DateTime }}
 */
export function getDateRange(value, offset = 0) {
    if (!value) {
        return {};
    }
    const now = DateTime.local();
    switch (value.type) {
        case "month":
        case "quarter":
        case "year":
            return getFixedPeriodFromTo(now, offset, value);
        case "relative":
            return getRelativeDateFromTo(now, offset, value.period);
        case "range":
            return {
                from: value.from && DateTime.fromISO(value.from).startOf("day"),
                to: value.to && DateTime.fromISO(value.to).endOf("day"),
            };
    }
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

export function getRelativeDateFromTo(now, offset, period) {
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

/**
 * Compute the next date filter value.
 *
 * @param {DateValue | undefined} value
 * @returns {DateValue | undefined}
 */
export function getNextDateFilterValue(value) {
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
        case "relative":
            return getNextRelativeDateFilterValue(value);
        case "range":
            return getNextRangeDateFilterValue(value);
    }
    return undefined;
}

export function getPreviousDateFilterValue(value) {
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
        case "relative":
            return getPreviousRelativeDateFilterValue(value);
        case "range":
            return getPreviousRangeDateFilterValue(value);
    }
    return undefined;
}

/**
 * Compute the next relative date filter value.
 *
 * @param {RelativeDateValue} value
 * @returns {RelativeDateValue}
 */
function getNextRelativeDateFilterValue(value) {
    switch (value.period) {
        case "today":
        case "yesterday":
        case "last_7_days":
        case "last_30_days":
        case "last_90_days": {
            const { from, to } = getRelativeDateFromTo(DateTime.local(), 1, value.period);
            return {
                type: "range",
                from: from.toISODate(),
                to: to.toISODate(),
            };
        }
        case "last_12_months": {
            const { from, to } = getRelativeDateFromTo(DateTime.local(), 1, value.period);
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
 * Compute the previous relative date filter value.
 *
 * @param {RelativeDateValue} value
 * @returns {RelativeDateValue}
 */
function getPreviousRelativeDateFilterValue(value) {
    switch (value.period) {
        case "today":
        case "yesterday":
        case "last_7_days":
        case "last_30_days":
        case "last_90_days": {
            const { from, to } = getRelativeDateFromTo(DateTime.local(), -1, value.period);
            return {
                type: "range",
                from: from.toISODate(),
                to: to.toISODate(),
            };
        }
        case "last_12_months": {
            const { from, to } = getRelativeDateFromTo(DateTime.local(), -1, value.period);
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
export function getNextRangeDateFilterValue(value) {
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
export function getPreviousRangeDateFilterValue(value) {
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

export async function getFacetInfo(env, filter, filterValue) {
    let values;
    const separator = _t("or");
    switch (filter.type) {
        case "date": {
            if (!filterValue) {
                throw new Error("Should be defined at this point");
            }
            values = [dateFilterValueToString(filterValue)];
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
