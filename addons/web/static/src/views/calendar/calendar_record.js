// @ts-check

/** @module @web/views/calendar/calendar_record - Pure transformation of raw server records into normalized calendar event objects */

import { deserializeDate, deserializeDateTime } from "@web/core/l10n/dates";
/**
 * Transform a raw ORM record into a normalized calendar event object.
 *
 * Handles date/datetime deserialization, all-day detection, duration
 * computation, color mapping, and showTime logic.
 *
 * @param {Record<string, any>} rawRecord - server record from ORM searchRead
 * @param {Object} options
 * @param {Record<string, any>} options.fields - model field definitions
 * @param {Object} options.fieldMapping - arch field mapping (date_start, date_stop, etc.)
 * @param {boolean} options.isTimeHidden - arch isTimeHidden flag
 * @param {string} options.scale - current calendar scale
 * @param {boolean} options.isSmall - env.isSmall (responsive flag)
 * @returns {{ id: number, title: string, isAllDay: boolean, start: any, startType: string,
 *             end: any, endType: string, duration: number, colorIndex: any,
 *             isHatched: boolean, isStriked: boolean, isTimeHidden: boolean,
 *             isMonth: boolean, isSmall: boolean, rawRecord: Record<string, any> }}
 */
export function normalizeCalendarRecord(
    rawRecord,
    { fields, fieldMapping, isTimeHidden, scale, isSmall },
) {
    const startType = fields[fieldMapping.date_start].type;
    const isAllDay =
        startType === "date" ||
        (fieldMapping.all_day && rawRecord[fieldMapping.all_day]) ||
        false;
    let start = isAllDay
        ? deserializeDate(rawRecord[fieldMapping.date_start])
        : deserializeDateTime(rawRecord[fieldMapping.date_start]);

    let end = start;
    let endType = startType;
    if (fieldMapping.date_stop) {
        endType = fields[fieldMapping.date_stop].type;
        end = isAllDay
            ? deserializeDate(rawRecord[fieldMapping.date_stop])
            : deserializeDateTime(rawRecord[fieldMapping.date_stop]);
    }

    const duration = rawRecord[fieldMapping.date_delay] || 1;

    if (isAllDay) {
        start = start.startOf("day");
        end = end.startOf("day");
    }
    if (!fieldMapping.date_stop && duration) {
        end = start.plus({ hours: duration });
    }

    const showTime =
        !(fieldMapping.all_day && rawRecord[fieldMapping.all_day]) &&
        startType !== "date" &&
        start.day === end.day;

    const colorValue = rawRecord[fieldMapping.color];
    const colorIndex = Array.isArray(colorValue) ? colorValue[0] : colorValue;

    const title = rawRecord[fieldMapping.create_name_field || "display_name"];

    return {
        id: rawRecord.id,
        title,
        isAllDay,
        start,
        startType,
        end,
        endType,
        duration,
        colorIndex,
        isHatched: rawRecord["is_hatched"] || false,
        isStriked: rawRecord["is_striked"] || false,
        isTimeHidden: isTimeHidden || !showTime,
        isMonth: scale === "month",
        isSmall,
        rawRecord,
    };
}
