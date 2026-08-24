import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";

export function resolveTimeZoneName(tz) {
    return tz === "localtime" ? "local" : tz;
}

/**
 * @param {string} partnerTz resolved, and different from the current user one
 * @param {string} currentUserTz resolved
 * @param {import("luxon").DateTime<true>} now
 * @returns {Translation} the local time of the partner, translated
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
