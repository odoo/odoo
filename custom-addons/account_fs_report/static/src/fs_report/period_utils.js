/** Period helpers mirroring Enterprise account_reports date math (single / as-of mode). */

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
