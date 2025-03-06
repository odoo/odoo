import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

function range(start, stop) {
    const range = [];
    for (let i = start; i <= stop; i++) {
        range.push(i);
    }
    return range;
}

function isIntegerInRange(start, stop) {
    return (num) => Number.isInteger(num) && start <= num && num <= stop;
}

function getCurrent(unit) {
    return () => DateTime.now()[unit];
}

// we have to wait localization service -> better way to do this?
let DATETIME_OPTIONS_WITH_SELECT;
export function get_DATETIME_OPTIONS_WITH_SELECT() {
    if (!DATETIME_OPTIONS_WITH_SELECT) {
        const { weekStart } = localization;
        DATETIME_OPTIONS_WITH_SELECT = {
            month_number: {
                options: range(1, 12).map((month) => [
                    month,
                    luxon.DateTime.now().set({ month }).toFormat("MMMM"),
                ]),
                defaultValue: getCurrent("month"),
                isSupported: isIntegerInRange(1, 12),
            },
            quarter_number: {
                options: range(1, 4).map((quarter) => [
                    quarter,
                    _t("Quarter %(quarter)s", { quarter }),
                ]),
                defaultValue: getCurrent("quarter"),
                isSupported: isIntegerInRange(1, 4),
            },
            day_of_week: {
                options: range(0, 6).map((weekday) => [
                    (weekday + weekStart) % 7,
                    luxon.DateTime.now()
                        .set({ weekday: (weekday + weekStart) % 7 })
                        .toFormat("cccc"),
                ]),
                defaultValue: getCurrent("weekday"),
                isSupported: isIntegerInRange(0, 6),
            },
        };
    }
    return DATETIME_OPTIONS_WITH_SELECT;
}

let DATETIME_OPTIONS_WITH_INPUT;
export function get_DATETIME_OPTIONS_WITH_INPUT() {
    if (!DATETIME_OPTIONS_WITH_INPUT) {
        DATETIME_OPTIONS_WITH_INPUT = {
            year_number: {
                defaultValue: getCurrent("year"),
                isSupported: Number.isInteger,
            },
            day_of_year: {
                defaultValue: getCurrent("ordinal"),
                isSupported: isIntegerInRange(1, 366),
            },
            iso_week_number: {
                defaultValue: getCurrent("weekNumber"),
                isSupported: isIntegerInRange(1, 53),
            },
            hour_number: {
                defaultValue: getCurrent("hour"),
                isSupported: isIntegerInRange(0, 23),
            },
            minute_number: {
                defaultValue: getCurrent("minute"),
                isSupported: isIntegerInRange(0, 59),
            },
            second_number: {
                defaultValue: getCurrent("second"),
                isSupported: isIntegerInRange(0, 59),
            },
            day_of_month: {
                defaultValue: getCurrent("day"),
                isSupported: isIntegerInRange(1, 31),
            },
        };
    }
    return DATETIME_OPTIONS_WITH_INPUT;
}
