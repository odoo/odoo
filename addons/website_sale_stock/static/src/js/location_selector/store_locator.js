import { patch } from "@web/core/utils/patch";
import { locationBatchUtils } from "@website/builder/plugins/store_locator_utils";
import { _t } from "@web/core/l10n/translation";

// This patch provides the website snippet s_store_locator with the ability
// to read and display opening hours collected from stock.warehouse.
patch( locationBatchUtils, {
    async updateCalendar(orm, locationsMap, idsToUpdate) {
        const updateCalendarsProms = [];
        const calendars = await orm.searchRead(
            "stock.warehouse",
            [["partner_id", "in", idsToUpdate]],
            ["partner_id", "opening_hours"]
        );
        if (calendars) {
            calendars.forEach((entry) => {
                const partner_id = entry.partner_id[0];
                const calendar_id = entry.opening_hours[0];
                updateCalendarsProms.push(
                    orm
                        .searchRead(
                            "resource.calendar.attendance",
                            [
                                ["day_period", "!=", "lunch"],
                                ["calendar_id", "=", calendar_id],
                            ],
                            ["calendar_id", "dayofweek", "day_period", "hour_from", "hour_to"]
                        )
                        .then((opening_hours) => {
                            if (opening_hours.length) {
                                const loc = locationsMap.get(partner_id);
                                loc.opening_hours = formatOpeningHours(opening_hours);
                            }
                        })
                );
            });
        }
        await Promise.all(updateCalendarsProms);
    },
});

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
function formatOpeningHours(openingHours) {
    function toTimeString(time) {
        const hour = Math.floor(time);
        const minute = Math.round((time - hour) * 60)
        const timeString = luxon.DateTime.local().set({hour, minute}).toLocaleString(luxon.DateTime.TIME_SIMPLE)
        return timeString;
    }
    const formattedOpeningHours = Array.from({ length: 7 }, () => []);
    openingHours.forEach((period) => {
        formattedOpeningHours[period.dayofweek].push( toTimeString(period.hour_from) + " - " + toTimeString(period.hour_to));
    });
    return formattedOpeningHours;
}
