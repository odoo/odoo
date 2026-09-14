/** @odoo-module native */
import { registerImStatusDecoration } from "@mail/core/common/presence_status";
import { _t } from "@web/core/translation";

// hr_homeworking spells a located presence `<location_type>_<im_status>` on both
// res.users.im_status and res.partner.im_status. hr_holidays spells its own
// `leave_<im_status>` the same way, so the location word -- not the presence of
// an underscore -- is what identifies one of ours.
const LOCATIONS = {
    home: { icon: "fa-solid fa-house", label: _t("At Home") },
    office: { icon: "fa-solid fa-building", label: _t("At Office") },
    other: { icon: "fa-solid fa-location-dot", label: _t("At Other") },
};

/** @type {string[]} the location words this module decorates a status with */
export const WORK_LOCATION_TYPES = [];

const STATUSES = {
    online: { color: "text-success", label: _t("Online") },
    away: { color: "o-yellow", label: _t("Idle") },
    busy: { color: "text-danger", label: _t("Busy") },
    offline: { color: "text-body", label: _t("Offline") },
};

/**
 * @param {string|undefined|false} imStatus
 * @returns {{icon: string, color: string, title: string}|null}
 */
export function workLocationPresence(imStatus) {
    if (typeof imStatus !== "string") {
        return null;
    }
    const [locationType, status] = imStatus.split("_");
    const location = LOCATIONS[locationType];
    const presence = STATUSES[status];
    if (!location || !presence) {
        return null;
    }
    return {
        icon: location.icon,
        color: presence.color,
        title: `${location.label} - ${presence.label}`,
    };
}

// Tell mail what each located status means, once. Everything that reads a
// presence word -- the member partition, the chat bubble, the self-presence
// restart, offline_since -- answers from this rather than from a literal list
// repeated per reader.
export const WORK_LOCATION_PRESENCE_WORDS = Object.keys(STATUSES);

for (const locationType of Object.keys(LOCATIONS)) {
    WORK_LOCATION_TYPES.push(locationType);
    for (const status of WORK_LOCATION_PRESENCE_WORDS) {
        registerImStatusDecoration(`${locationType}_${status}`, status);
    }
}
