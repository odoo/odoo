/** @odoo-module **/

/**
 * Parses a pivot week header value.
 * @param {string} value
 * @example
 * parseServerWeekHeader("W1 2020") // { week: 1, year: 2020 }
 */
export function parseServerWeekHeader(value) {
    // Value is always formatted as "W1 2020", no matter the language.
    // Parsing this formatted value is the only way to ensure we get the same
    // locale aware week number as the one used in the server.
    const [week, year] = value.split(" ");
    return { week: Number(week.slice(1)), year: Number(year) };
}

export const VERSION = "1.0";

export function makeSortedColumn(params) {
    return {
        colGroupBys: [],
        groupId: [[], []],
        originIndedexs: [0],
        ...params,
        version: VERSION,
    };
}
