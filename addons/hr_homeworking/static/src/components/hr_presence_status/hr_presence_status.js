import { patch } from "@web/core/utils/patch";

import { HrPresenceStatus, hrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";
import { HrPresenceStatusPrivate, hrPresenceStatusPrivate } from "@hr/components/hr_presence_status_private/hr_presence_status_private";
import { _t } from "@web/core/l10n/translation";

const patchHrPresenceStatus = () => ({
    get color() {
        if (this.location) {
            let color = "text-muted";
            if (this.props.record.data.hr_presence_state !== "out_of_working_hour") {
                color = this.props.record.data.hr_presence_state === "present" ?  "text-success" : "o_icon_employee_absent";
            }
            return color;
        }
        return super.color;
    },

    get icon() {
        if (this.location) {
            switch (this.location) {
                case "home":
                    return "fa-home";
                case "office":
                    return "fa-building";
                case "other":
                    return "fa-map-marker";
            }
        }
        return super.icon;
    },

    get location() {
        return this.props.record.data.work_location_type;
    },

    get label() {
        if (this.location) {
            return this.props.record.data.work_location_name || _t("Unspecified");
        }
        return super.label;
    },
});

// for the both components: first applies the common patch and then applies patch for label
patch(HrPresenceStatus.prototype, patchHrPresenceStatus());
patch(HrPresenceStatusPrivate.prototype, patchHrPresenceStatus());

const additionalFieldDependencies = [
    { name: "hr_presence_state", type: "selection" },
    { name: "work_location_type", type: "char" },
    { name: "work_location_name", type: "char" },
];
if (typeof hrPresenceStatus.fieldDependencies === "function") {
    const oldFieldDependencies = hrPresenceStatus.fieldDependencies;
    hrPresenceStatus.fieldDependencies = (widgetInfo) => {
        const fieldDependencies = oldFieldDependencies(widgetInfo);
        fieldDependencies.push(...additionalFieldDependencies);
        return fieldDependencies;
    }
} else {
    hrPresenceStatus.fieldDependencies = [
        ...(hrPresenceStatus.fieldDependencies || []),
        ...additionalFieldDependencies,
    ];
}
hrPresenceStatusPrivate.fieldDependencies = [
    ...(hrPresenceStatusPrivate.fieldDependencies || []),
    ...additionalFieldDependencies,
];
