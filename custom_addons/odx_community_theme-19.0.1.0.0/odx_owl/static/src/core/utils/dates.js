/** @odoo-module **/

import { toRaw } from "@odoo/owl";

function isValidDate(date) {
    return date instanceof Date && !Number.isNaN(date.getTime());
}

export function createDate(year, month, day) {
    const date = new Date(year, month, day);
    date.setHours(0, 0, 0, 0);
    return date;
}

export function startOfDay(value) {
    const date = normalizeDateValue(value);
    return date ? createDate(date.getFullYear(), date.getMonth(), date.getDate()) : null;
}

export function today() {
    return startOfDay(new Date());
}

export function normalizeDateValue(value) {
    const rawValue = value && typeof value === "object" ? toRaw(value) : value;
    if (rawValue === undefined || rawValue === null || rawValue === "") {
        return null;
    }
    if (isValidDate(rawValue)) {
        return createDate(rawValue.getFullYear(), rawValue.getMonth(), rawValue.getDate());
    }
    if (typeof rawValue === "string") {
        const isoMatch = rawValue.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (isoMatch) {
            return createDate(Number(isoMatch[1]), Number(isoMatch[2]) - 1, Number(isoMatch[3]));
        }
    }
    if (typeof rawValue === "number" || typeof rawValue === "string") {
        const date = new Date(rawValue);
        if (isValidDate(date)) {
            return createDate(date.getFullYear(), date.getMonth(), date.getDate());
        }
    }
    return null;
}

export function addDays(value, count) {
    const date = normalizeDateValue(value);
    return date
        ? createDate(date.getFullYear(), date.getMonth(), date.getDate() + Number(count || 0))
        : null;
}

export function addMonths(value, count) {
    const date = normalizeDateValue(value);
    if (!date) {
        return null;
    }
    const targetMonth = date.getMonth() + Number(count || 0);
    const base = createDate(date.getFullYear(), targetMonth, 1);
    const lastDay = endOfMonth(base).getDate();
    return createDate(base.getFullYear(), base.getMonth(), Math.min(date.getDate(), lastDay));
}

export function compareDays(left, right) {
    const leftDate = normalizeDateValue(left);
    const rightDate = normalizeDateValue(right);
    if (!leftDate && !rightDate) {
        return 0;
    }
    if (!leftDate) {
        return -1;
    }
    if (!rightDate) {
        return 1;
    }
    return leftDate.getTime() - rightDate.getTime();
}

export function endOfMonth(value) {
    const date = normalizeDateValue(value);
    return date ? createDate(date.getFullYear(), date.getMonth() + 1, 0) : null;
}

export function endOfWeek(value, weekStartsOn = 0) {
    const date = normalizeDateValue(value);
    if (!date) {
        return null;
    }
    return addDays(startOfWeek(date, weekStartsOn), 6);
}

export function findNearestEnabledDate(value, options = {}, direction = 1, limit = 366) {
    let current = normalizeDateValue(value);
    if (!current) {
        return null;
    }
    for (let index = 0; index < limit; index++) {
        if (!isDateDisabled(current, options)) {
            return current;
        }
        current = addDays(current, direction >= 0 ? 1 : -1);
    }
    return null;
}

export function formatDateValue(value, options = {}, locale) {
    const date = normalizeDateValue(value);
    return date ? new Intl.DateTimeFormat(locale, options).format(date) : "";
}

export function formatDateRangeValue(value, options = {}, locale) {
    const range = normalizeDateRange(value);
    if (!range?.from) {
        return "";
    }
    if (!range.to || isSameDay(range.from, range.to)) {
        return formatDateValue(range.from, options, locale);
    }
    return `${formatDateValue(range.from, options, locale)} - ${formatDateValue(
        range.to,
        options,
        locale
    )}`;
}

export function resolveWeekStartsOn(weekStartsOn, locale, fallback = 0) {
    if (Number.isInteger(weekStartsOn) && weekStartsOn >= 0 && weekStartsOn <= 6) {
        return weekStartsOn;
    }

    try {
        const resolvedLocale =
            locale ||
            new Intl.DateTimeFormat().resolvedOptions().locale ||
            undefined;
        if (typeof Intl !== "undefined" && Intl.Locale && resolvedLocale) {
            const localeInfo = new Intl.Locale(resolvedLocale);
            const weekInfo = localeInfo.weekInfo || localeInfo.getWeekInfo?.();
            if (weekInfo && typeof weekInfo.firstDay === "number") {
                return weekInfo.firstDay % 7;
            }
        }
    } catch {
        // Fall back to the provided default when locale week info is unavailable.
    }

    return fallback;
}

export function getMonthWeeks(value, options = {}) {
    const monthDate = startOfMonth(value);
    if (!monthDate) {
        return [];
    }

    const weekStartsOn = Number(options.weekStartsOn ?? 0);
    const fixedWeeks = options.fixedWeeks !== false;
    const start = startOfWeek(monthDate, weekStartsOn);
    const end = fixedWeeks ? addDays(start, 41) : endOfWeek(endOfMonth(monthDate), weekStartsOn);
    const weeks = [];

    let cursor = start;
    while (cursor && compareDays(cursor, end) <= 0) {
        const week = [];
        for (let index = 0; index < 7; index++) {
            const current = addDays(cursor, index);
            week.push({
                date: current,
                isOutside: current.getMonth() !== monthDate.getMonth(),
            });
        }
        weeks.push(week);
        cursor = addDays(cursor, 7);
    }
    return weeks;
}

export function getWeekdayLabels(weekStartsOn = 0, locale, width = "short") {
    const baseDate = createDate(2024, 0, 7);
    return Array.from({ length: 7 }, (_, index) =>
        formatDateValue(addDays(baseDate, (weekStartsOn + index) % 7), { weekday: width }, locale)
    );
}

export function isDateDisabled(value, options = {}) {
    const date = normalizeDateValue(value);
    if (!date) {
        return true;
    }

    const minDate = normalizeDateValue(options.minDate);
    const maxDate = normalizeDateValue(options.maxDate);
    if (minDate && compareDays(date, minDate) < 0) {
        return true;
    }
    if (maxDate && compareDays(date, maxDate) > 0) {
        return true;
    }

    const disabledDates = options.disabledDates;
    if (!disabledDates) {
        return false;
    }
    if (typeof disabledDates === "function") {
        return Boolean(disabledDates(date));
    }
    if (!Array.isArray(disabledDates)) {
        return false;
    }
    return disabledDates.some((matcher) => {
        if (typeof matcher === "function") {
            return Boolean(matcher(date));
        }
        return isSameDay(date, matcher);
    });
}

export function isDateInRange(value, range) {
    const date = normalizeDateValue(value);
    const normalizedRange = normalizeDateRange(range);
    if (!date || !normalizedRange?.from) {
        return false;
    }
    if (!normalizedRange.to) {
        return isSameDay(date, normalizedRange.from);
    }
    return (
        compareDays(date, normalizedRange.from) >= 0 &&
        compareDays(date, normalizedRange.to) <= 0
    );
}

export function isSameDay(left, right) {
    const leftDate = normalizeDateValue(left);
    const rightDate = normalizeDateValue(right);
    return Boolean(leftDate && rightDate && compareDays(leftDate, rightDate) === 0);
}

export function isRangeComplete(value) {
    const range = normalizeDateRange(value);
    return Boolean(range?.from && range?.to);
}

export function isSameMonth(left, right) {
    const leftDate = normalizeDateValue(left);
    const rightDate = normalizeDateValue(right);
    return Boolean(
        leftDate &&
        rightDate &&
        leftDate.getFullYear() === rightDate.getFullYear() &&
        leftDate.getMonth() === rightDate.getMonth()
    );
}

export function startOfMonth(value) {
    const date = normalizeDateValue(value);
    return date ? createDate(date.getFullYear(), date.getMonth(), 1) : null;
}

export function startOfWeek(value, weekStartsOn = 0) {
    const date = normalizeDateValue(value);
    if (!date) {
        return null;
    }
    const offset = (date.getDay() - Number(weekStartsOn) + 7) % 7;
    return addDays(date, -offset);
}

export function normalizeDateRange(value) {
    const rawValue = value && typeof value === "object" ? toRaw(value) : value;
    if (!rawValue || typeof rawValue !== "object") {
        return null;
    }
    const from = normalizeDateValue(rawValue.from);
    const to = normalizeDateValue(rawValue.to);
    if (!from && !to) {
        return null;
    }
    if (from && to && compareDays(from, to) > 0) {
        return { from: to, to: from };
    }
    return {
        from: from || to,
        to: from ? to : to,
    };
}

export function toISODateRange(value) {
    const range = normalizeDateRange(value);
    return {
        from: toISODate(range?.from),
        to: toISODate(range?.to),
    };
}

export function toISODate(value) {
    const date = normalizeDateValue(value);
    return date
        ? `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(
              date.getDate()
          ).padStart(2, "0")}`
        : "";
}
