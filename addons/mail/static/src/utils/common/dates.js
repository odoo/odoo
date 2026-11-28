import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { user } from "@web/core/user";

const { DateTime } = luxon;

export function resolveTimeZoneName(tz) {
    return tz === "localtime" ? "local" : tz;
}

/**
 * @param {string} partnerTz resolved, and different from the current user one
 * @param {string} currentUserTz resolved
 * @param {import("luxon").DateTime<true>} now
 * @returns the local time of the partner, translated
 */
export function formatLocalDateTime(partnerTz, currentUserTz, now) {
    const partnerDateTime = now.setZone(partnerTz);
    const currentUserDateTime = now.setZone(currentUserTz);
    const format = currentUserDateTime.hasSame(partnerDateTime, "day")
        ? localization.timeFormat.replace(":ss", "")
        : localization.dateTimeFormat.replace(":ss", "");
    const datetime = partnerDateTime.toFormat(format);
    return _t("%(datetime)s local time", { datetime });
}

/**
 * @param {import("luxon").DateTime<true>} datetime
 * @param {import("luxon").DateTime<true>} startOfToday read from the store, so
 *   that callers in a computed are refreshed when the day changes
 * @returns {string}
 */
export function formatDateSimpleWithDay(datetime, startOfToday) {
    const userLocale = { locale: user.lang };
    if (datetime.hasSame(startOfToday, "day")) {
        return datetime.toLocaleString(DateTime.TIME_SIMPLE, userLocale);
    }
    if (datetime.hasSame(startOfToday.minus({ day: 1 }), "day")) {
        return _t("Yesterday at %(time)s", {
            time: datetime.toLocaleString(DateTime.TIME_SIMPLE, userLocale),
        });
    }
    if (datetime.hasSame(startOfToday, "year")) {
        return datetime.toLocaleString({ ...DateTime.DATETIME_MED, year: undefined }, userLocale);
    }
    return datetime.toLocaleString(DateTime.DATETIME_MED, userLocale);
}

/**
 * @param {import("luxon").DateTime<true>} datetime
 * @returns {string}
 */
export function formatDatetimeMedium(datetime) {
    return datetime.toLocaleString(DateTime.DATETIME_MED, { locale: user.lang });
}
