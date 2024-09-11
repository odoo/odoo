/** @odoo-module */
// @ts-check

import { _t } from "@web/core/l10n/translation";

export const DEFAULT_LINES_NUMBER = 20;

export const UNTITLED_SPREADSHEET_NAME = _t("Untitled spreadsheet");

export const RELATIVE_DATE_RANGE_TYPES = [
    { type: "year_to_date", description: _t("Year to Date") },
    { type: "last_week", description: _t("Last 7 Days") },
    { type: "last_month", description: _t("Last 30 Days") },
    { type: "last_three_months", description: _t("Last 90 Days") },
    { type: "last_six_months", description: _t("Last 180 Days") },
    { type: "last_year", description: _t("Last 365 Days") },
    { type: "last_three_years", description: _t("Last 3 Years") },
];
