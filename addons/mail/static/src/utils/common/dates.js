import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";

const { DateTime } = luxon;

function resolveTimeZoneName(tz) {
    return tz === "localtime" ? "local" : tz;
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
        [resolvedPartnerTz, resolvedCurrentUserTz].includes("local") ||
        resolvedPartnerTz === resolvedCurrentUserTz
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
