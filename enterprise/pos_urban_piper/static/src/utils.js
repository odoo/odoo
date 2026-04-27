import { user } from "@web/core/user";

/**
 * This method converts time from milliseconds to the user's time zone.
 */
export function getTime(time) {
    const formattedTime = Intl.DateTimeFormat("en-US", {
        timeZone: user.tz || luxon.Settings.defaultZone.name,
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    }).format(time);
    return formattedTime;
}
