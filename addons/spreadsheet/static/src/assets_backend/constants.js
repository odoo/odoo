/** @odoo-module */

import { _lt } from "@web/core/l10n/translation";

export const FILTER_DATE_OPTION = {
    quarter: ["first_quarter", "second_quarter", "third_quarter", "fourth_quarter"],
    year: ["this_year", "last_year", "antepenultimate_year"],
};

// TODO Remove this mapping, We should only need number > description to avoid multiple conversions
// This would require a migration though
export const monthsOptions = [
    { id: "january", description: _lt("January") },
    { id: "february", description: _lt("February") },
    { id: "march", description: _lt("March") },
    { id: "april", description: _lt("April") },
    { id: "may", description: _lt("May") },
    { id: "june", description: _lt("June") },
    { id: "july", description: _lt("July") },
    { id: "august", description: _lt("August") },
    { id: "september", description: _lt("September") },
    { id: "october", description: _lt("October") },
    { id: "november", description: _lt("November") },
    { id: "december", description: _lt("December") },
];
