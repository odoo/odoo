/** @odoo-module native */
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

// The presence words a located status can carry and still count as reachable.
// mail's `onlineMemberStatuses` is a membership test against literal strings, so
// a located status is absent from it and its member falls into Discuss's Offline
// section while the person is at their desk.
const REACHABLE = ["online", "away", "busy"];

export const REACHABLE_WORK_LOCATION_STATUSES = Object.keys(LOCATIONS).flatMap(
    (locationType) => REACHABLE.map((status) => `${locationType}_${status}`),
);
