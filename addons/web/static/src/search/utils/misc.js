// @ts-check

/** @module @web/search/utils/misc - Shared constants for search facet icons, colors, and groupable field types */

/** Icon classes for each search facet type. */
export const FACET_ICONS = {
    filter: "fa fa-filter",
    groupBy: "oi oi-group",
    groupByAsc: "fa fa-sort-numeric-asc",
    groupByDesc: "fa fa-sort-numeric-desc",
    favorite: "fa fa-star",
};

/** Bootstrap color variants for each search facet type. */
export const FACET_COLORS = {
    filter: "primary",
    groupBy: "action",
    favorite: "warning",
};

/** @type {string[]} Field types that support the "Group By" operation. */
export const GROUPABLE_TYPES = [
    "boolean",
    "char",
    "date",
    "datetime",
    "integer",
    "many2one",
    "many2many",
    "selection",
    "tags",
];
