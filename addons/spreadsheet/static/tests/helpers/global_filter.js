/**
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").GlobalFilter} GlobalFilter
 *
 */

/** @type FixedPeriodDateGlobalFilter */
export const THIS_YEAR_GLOBAL_FILTER = {
    id: "43",
    label: "This Year",
    operator: "fixedPeriod",
    defaultValue: { yearOffset: 0 },
};

/** @type FixedPeriodDateGlobalFilter */
export const LAST_YEAR_GLOBAL_FILTER = {
    id: "42",
    label: "Last Year",
    operator: "fixedPeriod",
    defaultValue: { yearOffset: -1 },
};

/** @type FixedPeriodDateGlobalFilter */
export const NEXT_YEAR_GLOBAL_FILTER = {
    id: "44",
    label: "Next Year",
    operator: "fixedPeriod",
    defaultValue: { yearOffset: 1 },
};
