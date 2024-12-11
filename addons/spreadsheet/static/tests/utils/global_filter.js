/** @odoo-module */

/**
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").GlobalFilter} GlobalFilter
 *
 */

/** @type FixedPeriodDateGlobalFilter */
export const THIS_YEAR_GLOBAL_FILTER = {
    id: "43",
    type: "date",
    label: "This Year",
    rangeType: "fixedPeriod",
    defaultValue: { yearOffset: 0 },
};

/** @type FixedPeriodDateGlobalFilter */
export const LAST_YEAR_GLOBAL_FILTER = {
    id: "42",
    type: "date",
    label: "Last Year",
    rangeType: "fixedPeriod",
    defaultValue: { yearOffset: -1 },
};

/** @type FixedPeriodDateGlobalFilter */
export const NEXT_YEAR_GLOBAL_FILTER = {
    id: "44",
    type: "date",
    label: "Next Year",
    rangeType: "fixedPeriod",
    defaultValue: { yearOffset: 1 },
};
