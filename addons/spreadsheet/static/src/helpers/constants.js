// @ts-check

import { _t } from "@web/core/l10n/translation";

export const DEFAULT_LINES_NUMBER = 20;

export const UNTITLED_SPREADSHEET_NAME = _t("Untitled spreadsheet");

export const RELATIVE_DATE_RANGE_TYPES = [
    { type: "last_7_days", description: _t("Last 7 Days") },
    { type: "last_30_days", description: _t("Last 30 Days") },
    { type: "last_90_days", description: _t("Last 90 Days") },
    { type: "last_12_months", description: _t("Last 12 Months") },
    { type: "year_to_date", description: _t("Year to Date") },
];
