import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";

const { DateTime } = luxon;

function resolveTimeZoneName(tz) {
    return tz === "localtime" ? "local" : tz;
}

/**
 * @param {luxon.DateTime} datetime
 */
export function computeDelay(datetime) {
    if (!datetime) {
        return 0;
    }
    const today = DateTime.now().startOf("day");
    return datetime.diff(today, "days").days;
}

/**
 * @param {string} partnerTz
 * @param {string} currentUserTz
 */
export function formatLocalDateTime(partnerTz, currentUserTz) {
    const resolvedCurrentUserTz = resolveTimeZoneName(currentUserTz);
    const resolvedPartnerTz = resolveTimeZoneName(partnerTz);
    if (
        !resolvedPartnerTz ||
        !resolvedCurrentUserTz ||
        [resolvedPartnerTz, resolvedCurrentUserTz].includes("local")
    ) {
        return null;
    }
    const now = DateTime.now();
    const partnerDateTime = now.setZone(resolvedPartnerTz);
    const currentUserDateTime = now.setZone(resolvedCurrentUserTz);
    const format = currentUserDateTime.hasSame(partnerDateTime, "day")
        ? localization.timeFormat.replace(":ss", "")
        : localization.dateTimeFormat.replace(":ss", "");
    const datetime = partnerDateTime.toFormat(format);
    return _t("%(datetime)s local time", { datetime });
}

export function getMsToTomorrow() {
    const now = new Date();
    const night = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate() + 1, // the next day
        0,
        0,
        0 // at 00:00:00 hours
    );
    return night.getTime() - now.getTime();
}

export function isToday(datetime) {
    if (!datetime) {
        return false;
    }
    return (
        datetime.toLocaleString(DateTime.DATE_FULL) ===
        DateTime.now().toLocaleString(DateTime.DATE_FULL)
    );
}
