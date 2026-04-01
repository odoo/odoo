import { _t } from "@web/core/l10n/translation";

/**
 * Formats opening hours information to make it compatible with the
 * LocationSelectorComponent. Returns an object containing an array of strings
 * for each day of the week. The strings are time periods in the format
 * "start_time - end_time".
 *
 * @param {Array} openingHours list of opening period objects to format
 *
 * @returns {Object}
 */
export function formatOpeningHours(openingHours) {
    function toTimeString(hour) {
        const hFloor = Math.floor(hour);
        const h = hFloor.toString();
        const m = Math.round((hour - hFloor) * 60)
            .toString()
            .padStart(2, "0");
        return { h, m };
    }
    const formattedOpeningHours = {
        0: [],
        1: [],
        2: [],
        3: [],
        4: [],
        5: [],
        6: [],
    };
    openingHours.forEach((period) => {
        const { h: hour_from, m: minute_from } = toTimeString(period.hour_from);
        const { h: hour_to, m: minute_to } = toTimeString(period.hour_to);
        formattedOpeningHours[period.dayofweek].push(
            _t("%(hour_from)s:%(minute_from)s - %(hour_to)s:%(minute_to)s", {
                hour_from,
                minute_from,
                hour_to,
                minute_to,
            })
        );
    });
    return formattedOpeningHours;
}
