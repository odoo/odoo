// @ts-check

/** @module @web/views/calendar/calendar_date_range - Pure date range computation and domain construction for calendar views */

import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
/**
 * Compute the visible date range for a given calendar scale.
 *
 * For week scale, aligns to the configured first day of week.
 * For month with overflow, extends to full weeks (6 rows).
 *
 * @param {string} scale - "day" | "week" | "month" | "year"
 * @param {any} date - Luxon DateTime, the anchor date
 * @param {number} firstDayOfWeek - 0=Sunday, 1=Monday, etc.
 * @param {boolean} monthOverflow - whether month view shows overflow weeks
 * @returns {{ start: any, end: any }} Luxon DateTime range (start of day / end of day)
 */
export function computeCalendarRange(scale, date, firstDayOfWeek, monthOverflow) {
    let start = date;
    let end = date;

    if (scale !== "week") {
        // startOf("week") does not depend on locale and will always give the
        // "Monday" of the week...
        start = start.startOf(scale);
        end = end.endOf(scale);
    }

    if (scale === "week" || (scale === "month" && monthOverflow)) {
        const currentWeekOffset = (start.weekday - firstDayOfWeek + 7) % 7;
        start = start.minus({ days: currentWeekOffset });
        end = start.plus({ weeks: scale === "week" ? 1 : 6, days: -1 });
    }

    start = start.startOf("day");
    end = end.endOf("day");

    return { start, end };
}

/**
 * Build a domain restricting records to those overlapping the given date range.
 *
 * @param {{ date_start: string, date_stop?: string, date_delay?: string }} fieldMapping
 * @param {"date" | "datetime"} dateStartType - type of the date_start field
 * @param {{ start: any, end: any }} range - computed range from computeCalendarRange
 * @returns {any[][]} Odoo domain tuples
 */
export function computeRangeDomain(fieldMapping, dateStartType, range) {
    const serializeFn = dateStartType === "date" ? serializeDate : serializeDateTime;
    const formattedEnd = serializeFn(range.end);
    const formattedStart = serializeFn(range.start);

    const domain = [[fieldMapping.date_start, "<=", formattedEnd]];
    if (fieldMapping.date_stop) {
        domain.push([fieldMapping.date_stop, ">=", formattedStart]);
    } else if (!fieldMapping.date_delay) {
        domain.push([fieldMapping.date_start, ">=", formattedStart]);
    }
    return domain;
}

/**
 * Build a domain from active/inactive filter sections.
 *
 * Static filters (with writeResModel) use "in" for active values.
 * Dynamic filters use "not in" for inactive values.
 *
 * @param {Record<string, { filters: { active: boolean, value: any }[] }>} filterSections
 * @param {Record<string, { writeResModel?: string }>} filtersInfo
 * @returns {any[][]} Odoo domain tuples
 */
export function computeFiltersDomain(filterSections, filtersInfo) {
    const authorizedValues = {};
    const avoidValues = {};

    for (const [fieldName, filterSection] of Object.entries(filterSections)) {
        const filterSectionInfo = filtersInfo[fieldName];
        for (const filter of filterSection.filters) {
            if (filterSectionInfo.writeResModel) {
                if (!authorizedValues[fieldName]) {
                    authorizedValues[fieldName] = [];
                }
                if (filter.active) {
                    authorizedValues[fieldName].push(filter.value);
                }
            } else {
                if (!filter.active) {
                    if (!avoidValues[fieldName]) {
                        avoidValues[fieldName] = [];
                    }
                    avoidValues[fieldName].push(filter.value);
                }
            }
        }
    }

    const domain = [];
    for (const field in authorizedValues) {
        domain.push([field, "in", authorizedValues[field]]);
    }
    for (const field in avoidValues) {
        if (avoidValues[field].length > 0) {
            domain.push([field, "not in", avoidValues[field]]);
        }
    }
    return domain;
}
