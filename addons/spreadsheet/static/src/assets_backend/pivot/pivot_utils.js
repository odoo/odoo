/** @odoo-module */

import { deserializeDate } from "@web/core/l10n/dates";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

const { DateTime } = luxon;

/**
 * @typedef {import("@spreadsheet/data_sources/metadata_repository").Field} Field
 */

export function normalizeServerValue(aggregateOperator, groupBy, field, readGroupResult) {
    if (readGroupResult[groupBy] === false) {
        return false;
    }
    switch (aggregateOperator) {
        case "day": {
            const serverDayValue = getGroupStartingDay(field, groupBy, readGroupResult);
            const date = deserializeDate(serverDayValue);
            return date.toFormat("MM/dd/yyyy");
        }
        case "week": {
            const weekValue = readGroupResult[groupBy];
            const { week, year } = parseServerWeekHeader(weekValue);
            return `${week}/${year}`;
        }
        case "month": {
            const firstOfTheMonth = getGroupStartingDay(field, groupBy, readGroupResult);
            const date = deserializeDate(firstOfTheMonth);
            return date.toFormat("MM/yyyy");
        }
        case "quarter": {
            const firstOfTheQuarter = getGroupStartingDay(field, groupBy, readGroupResult);
            const date = deserializeDate(firstOfTheQuarter);
            return `${date.quarter}/${date.year}`;
        }
        case "year": {
            return Number(readGroupResult[groupBy]);
        }
    }
}

/**
 * When grouping by a time field, return
 * the group starting day (local to the timezone)
 * @param {object} field
 * @param {string} groupBy
 * @param {object} readGroup
 * @returns {string | undefined}
 */
function getGroupStartingDay(field, groupBy, readGroup) {
    if (!readGroup["__range"] || !readGroup["__range"][groupBy]) {
        return undefined;
    }
    const sqlValue = readGroup["__range"][groupBy].from;
    if (field.type === "date") {
        return sqlValue;
    }
    const userTz = session.user_context.tz || luxon.Settings.defaultZoneName;
    return DateTime.fromSQL(sqlValue, { zone: "utc" }).setZone(userTz).toISODate();
}

/**
 * Parses a pivot week header value.
 * @param {string} value
 * @example
 * parseServerWeekHeader("W1 2020") // { week: 1, year: 2020 }
 */
function parseServerWeekHeader(value) {
    // Value is always formatted as "W1 2020", no matter the language.
    // Parsing this formatted value is the only way to ensure we get the same
    // locale aware week number as the one used in the server.
    const [week, year] = value.split(" ");
    return { week: Number(week.slice(1)), year: Number(year) };
}

/**
 * Determines if the given field is a date or datetime field.
 *
 * @param {Field} field Field description
 * @private
 * @returns {boolean} True if the type of the field is date or datetime
 */
export function isDateField(field) {
    return ["date", "datetime"].includes(field.type);
}

/**
 * Parses the positional char (#), the field and operator string of pivot group.
 * e.g. "create_date:month"
 * @param {Record<string, Field>} allFields
 * @param {string} groupFieldString
 * @returns {{field: Field, aggregateOperator: string, isPositional: boolean}}
 */
export function parseGroupField(allFields, groupFieldString) {
    let fieldName = groupFieldString;
    let aggregateOperator = undefined;
    const index = groupFieldString.indexOf(":");
    if (index !== -1) {
        fieldName = groupFieldString.slice(0, index);
        aggregateOperator = groupFieldString.slice(index + 1);
    }
    const isPositional = fieldName.startsWith("#");
    fieldName = isPositional ? fieldName.substring(1) : fieldName;
    const field = allFields[fieldName];
    if (field === undefined) {
        throw new Error(sprintf(_t("Field %s does not exist"), fieldName));
    }
    if (["date", "datetime"].includes(field.type)) {
        aggregateOperator = aggregateOperator || "month";
    }
    return {
        isPositional,
        field,
        aggregateOperator,
    };
}
