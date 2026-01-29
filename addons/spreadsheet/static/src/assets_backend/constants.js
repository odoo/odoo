/** @odoo-module */

import { _t } from "@web/core/l10n/translation";

export const FILTER_DATE_OPTION = {
    quarter: ["first_quarter", "second_quarter", "third_quarter", "fourth_quarter"],
};

// TODO Remove this mapping, We should only need number > description to avoid multiple conversions
// This would require a migration though
export const monthsOptions = [
    { id: "january", description: _t("January") },
    { id: "february", description: _t("February") },
    { id: "march", description: _t("March") },
    { id: "april", description: _t("April") },
    { id: "may", description: _t("May") },
    { id: "june", description: _t("June") },
    { id: "july", description: _t("July") },
    { id: "august", description: _t("August") },
    { id: "september", description: _t("September") },
    { id: "october", description: _t("October") },
    { id: "november", description: _t("November") },
    { id: "december", description: _t("December") },
];
