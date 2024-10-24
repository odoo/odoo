/** @odoo-module */
// @ts-check

import { _t } from "@web/core/l10n/translation";

export const DEFAULT_LINES_NUMBER = 20;

export const UNTITLED_SPREADSHEET_NAME = _t("Untitled spreadsheet");

export const RELATIVE_DATE_RANGE_REFERENCES = [
    { type: "last", description: _t("Last") },
    { type: "this", description: _t("This") },
    { type: "next", description: _t("Next") },
];

export const RELATIVE_DATE_RANGE_UNITS = [
    { type: "day", description: _t("Day(s)") },
    { type: "week_to_date", description: _t("Week(s) to Date") },
    { type: "week", description: _t("Week(s)") },
    { type: "month_to_date", description: _t("Month(s) to Date") },
    { type: "month", description: _t("Month(s)") },
    { type: "quarter", description: _t("Quarter(s)") },
    { type: "year_to_date", description: _t("Year(s) to Date") },
    { type: "year", description: _t("Year(s)") },
];
