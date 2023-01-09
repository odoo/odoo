/** @odoo-module */

import { _lt } from "@web/core/l10n/translation";

export const DEFAULT_LINES_NUMBER = 20;

export const FORMATS = {
    day: { out: "MM/DD/YYYY", display: "DD MMM YYYY", interval: "d" },
    week: { out: "WW/YYYY", display: "[W]W YYYY", interval: "w" },
    month: { out: "MM/YYYY", display: "MMMM YYYY", interval: "M" },
    quarter: { out: "Q/YYYY", display: "[Q]Q YYYY", interval: "Q" },
    year: { out: "YYYY", display: "YYYY", interval: "y" },
};

export const HEADER_STYLE = { fillColor: "#f2f2f2" };
export const TOP_LEVEL_STYLE = { bold: true, fillColor: "#f2f2f2" };
export const MEASURE_STYLE = { fillColor: "#f2f2f2", textColor: "#756f6f" };

export const UNTITLED_SPREADSHEET_NAME = _lt("Untitled spreadsheet");

export const RELATIVE_DATE_RANGE_TYPES = [
    { type: "last_week", description: _lt("Last 7 Days") },
    { type: "last_month", description: _lt("Last 30 Days") },
    { type: "last_three_months", description: _lt("Last 90 Days") },
    { type: "last_six_months", description: _lt("Last 180 Days") },
    { type: "last_year", description: _lt("Last 365 Days") },
    { type: "last_three_years", description: _lt("Last 3 Years") },
];
