import { _t } from "@web/core/l10n/translation";
import { t } from "@odoo/owl";

const LOCATION = t.object({
    id: t.or([t.string(), t.number()]),
    name: t.string(),
    opening_hours: t.object().optional({}),
    street: t.string(),
    city: t.string(),
    zip_code: t.string(),
    state: t.string().optional(),
    country_code: t.or([t.string(), t.array(t.or([t.number(), t.string()]))]),
    additional_data: t.object().optional({}),
    distance: t.number().optional(),
    latitude: t.or([t.string(), t.number()]),
    longitude: t.or([t.string(), t.number()]),
});

export const LOCATION_LIST = t.array(LOCATION);

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
