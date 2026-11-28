/** Period helpers mirroring Enterprise account_reports date math (single + range). */

import { _t } from "@web/core/l10n/translation";
import { formatDate } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export function computePeriodRange(date, startDay, startMonth, monthsPerPeriod) {
    const alignedDate = date.minus({ days: startDay - 1 });
    let year = alignedDate.year;
    const monthOffset = alignedDate.month - startMonth;
    let periodNumber = Math.floor(monthOffset / monthsPerPeriod) + 1;

    if (date < DateTime.utc(year, startMonth, startDay)) {
        year -= 1;
        periodNumber = Math.floor((12 + monthOffset) / monthsPerPeriod) + 1;
    }

    const deltaMonth = periodNumber * monthsPerPeriod;
    const endDate = DateTime.utc(year, startMonth, 1).plus({
        months: deltaMonth,
        days: startDay - 2,
    });
    const startDate = DateTime.utc(year, startMonth, 1)
        .plus({ months: deltaMonth - monthsPerPeriod })
        .set({ day: startDay });
    return [startDate.startOf("day"), endDate.startOf("day")];
}

export function monthsPerPeriodForType(periodType) {
    if (periodType === "quarter") {
        return 3;
    }
    if (periodType === "month") {
        return 1;
    }
    return 12;
}

/**
 * Shift as-of date to the previous period (Enterprise _get_shifted_dates_period, side=-1, single mode).
 */
export function shiftPreviousPeriodDate(dateTo, periodType, fiscalStartDay, fiscalStartMonth) {
    let type = periodType;
    if (type === "today" || type === "custom") {
        type = "year";
    }
    const months = monthsPerPeriodForType(type);
    const [dateFrom] = computePeriodRange(dateTo, fiscalStartDay, fiscalStartMonth, months);
    const reference = dateFrom.minus({ days: 1 });
    const [, newDateTo] = computePeriodRange(reference, fiscalStartDay, fiscalStartMonth, months);
    return newDateTo;
}

export function shiftSameLastYearDate(dateTo) {
    return dateTo.minus({ years: 1 }).startOf("day");
}

/**
 * Enterprise _get_shifted_dates_period for range_mode (side=-1).
 * @returns {[DateTime, DateTime]}
 */
export function shiftPreviousPeriodRange(dateFrom, dateTo, periodType, fiscalStartDay, fiscalStartMonth) {
    let type = periodType;
    if (type === "custom" || type === "today") {
        type = "year";
    }
    const months = monthsPerPeriodForType(type);
    const reference = dateFrom.minus({ days: 1 });
    return computePeriodRange(reference, fiscalStartDay, fiscalStartMonth, months);
}

/**
 * Enterprise same_last_year for range_mode.
 * @returns {[DateTime, DateTime]}
 */
export function shiftSameLastYearRange(dateFrom, dateTo) {
    return [dateFrom.minus({ years: 1 }).startOf("day"), dateTo.minus({ years: 1 }).startOf("day")];
}

/**
 * Enterprise _build_date_label (range_mode).
 */
export function buildRangeDateLabel(dateFrom, dateTo, periodType, fiscalStartDay = 1, fiscalStartMonth = 1) {
    const isCalendarAligned = fiscalStartDay === 1 && fiscalStartMonth === 1;
    const fromMonthStart = dateFrom.hasSame(dateFrom.startOf("month"), "day");
    const toMonthEnd = dateTo.hasSame(dateTo.endOf("month").startOf("day"), "day");
    const isFullCalendarYear =
        fromMonthStart &&
        toMonthEnd &&
        dateFrom.month === 1 &&
        dateTo.month === 12 &&
        dateFrom.year === dateTo.year;

    // Enterprise _build_date_label: calendar FY button shows "2025", not the full range.
    if (isCalendarAligned && isFullCalendarYear) {
        return formatDate(dateTo, { format: "yyyy" });
    }
    if (isCalendarAligned) {
        if (periodType === "month" || (fromMonthStart && toMonthEnd && dateFrom.month === dateTo.month && dateFrom.year === dateTo.year)) {
            return formatDate(dateTo, { format: "MMM yyyy" });
        }
        if (periodType === "quarter") {
            return _t("%(date_from)s - %(date_to)s", {
                date_from: formatDate(dateFrom, { format: "MMM" }),
                date_to: formatDate(dateTo, { format: "MMM yyyy" }),
            });
        }
        if (periodType === "year") {
            return formatDate(dateTo, { format: "yyyy" });
        }
    }

    if (fromMonthStart && toMonthEnd) {
        if (dateFrom.month === dateTo.month && dateFrom.year === dateTo.year) {
            return formatDate(dateTo, { format: "MMM yyyy" });
        }
        if (periodType === "year" || isFullCalendarYear) {
            return formatDate(dateTo, { format: "yyyy" });
        }
        return _t("%(date_from)s - %(date_to)s", {
            date_from: formatDate(dateFrom, { format: "MMM yyyy" }),
            date_to: formatDate(dateTo, { format: "MMM yyyy" }),
        });
    }
    return _t("%(date_from)s - %(date_to)s", {
        date_from: formatDate(dateFrom),
        date_to: formatDate(dateTo),
    });
}
