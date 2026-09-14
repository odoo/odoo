/** @odoo-module native */
import { patch } from "@web/core/utils/patch";

import {
    HrPresenceStatus,
    hrPresenceStatus,
} from "@hr/components/hr_presence_status/hr_presence_status";
import {
    HrPresenceStatusPrivate,
    hrPresenceStatusPrivate,
} from "@hr/components/hr_presence_status_private/hr_presence_status_private";
import {
    HrPresenceStatusPill,
    hrPresenceStatusPill,
} from "@hr/components/hr_presence_status_pill/hr_presence_status_pill";
import {
    HrPresenceStatusPrivatePill,
    hrPresenceStatusPrivatePill,
} from "@hr/components/hr_presence_status_private_pill/hr_presence_status_private_pill";
import { _t } from "@web/core/translation";

const LOCATION_ICONS = {
    home: "fa-home",
    office: "fa-building",
    other: "fa-map-marker",
};

const patchHrPresenceStatus = () => ({
    get color() {
        if (!this.location) {
            return super.color;
        }
        if (this.props.record.data.hr_presence_state === "out_of_working_hour") {
            return "text-muted";
        }
        return this.props.record.data.hr_presence_state === "present"
            ? "text-success"
            : "o_icon_employee_absent";
    },

    get icon() {
        return LOCATION_ICONS[this.location] ?? super.icon;
    },

    get location() {
        return this.props.record.data.work_location_type;
    },

    get label() {
        if (!this.location) {
            return super.label;
        }
        return this.props.record.data.work_location_name || _t("Unspecified");
    },
});

const patchHrPresenceStatusPill = () => ({
    get color() {
        if (!this.location) {
            return super.color;
        }
        if (this.props.record.data.hr_presence_state === "out_of_working_hour") {
            return "btn-outline-secondary text-muted";
        }
        return this.props.record.data.hr_presence_state === "present"
            ? "btn-outline-success"
            : "btn-outline-warning";
    },
});

patch(HrPresenceStatus.prototype, patchHrPresenceStatus());
patch(HrPresenceStatusPrivate.prototype, patchHrPresenceStatus());

patch(HrPresenceStatusPill.prototype, patchHrPresenceStatusPill());
patch(HrPresenceStatusPrivatePill.prototype, patchHrPresenceStatusPill());

const LOCATION_FIELD_DEPENDENCIES = [
    { name: "hr_presence_state", type: "selection" },
    { name: "work_location_type", type: "selection" },
    { name: "work_location_name", type: "char" },
];

// Each descriptor is a spread copy of hrPresenceStatus, so the four share one
// fieldDependencies array until a fresh one is assigned here.
for (const widget of [
    hrPresenceStatus,
    hrPresenceStatusPrivate,
    hrPresenceStatusPill,
    hrPresenceStatusPrivatePill,
]) {
    widget.fieldDependencies = [
        ...(widget.fieldDependencies ?? []),
        ...LOCATION_FIELD_DEPENDENCIES,
    ];
}
