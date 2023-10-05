/** @odoo-module **/

import { patch } from "@web/core/utils/patch";

import { HrPresenceStatus, hrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";
import { HrPresenceStatusPrivate, hrPresenceStatusPrivate } from "@hr/components/hr_presence_status_private/hr_presence_status_private";

const patchHrPresenceStatus = () => ({
    get color() {
        if (this.location) {
            let color = "text-muted";
            if (this.props.record.data.hr_presence_state !== "to_define") {
                color = this.props.record.data.hr_presence_state === "present" ?  "text-success" : "text-warning";
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
        let location = this.value?.split("_")[1] || "";
        if (location && !['home', 'office', 'other'].includes(location)) {
            location = "";
        }
        return location;
    },

    get label() {
        if (this.location) {
            return this.props.record.data.name_work_location_display;
        }
        return super.label;
    },
});

// for the both components: first applies the common patch and then applies patch for label
patch(HrPresenceStatus.prototype, patchHrPresenceStatus());
patch(HrPresenceStatusPrivate.prototype, patchHrPresenceStatus());

const additionalFieldDependencies = [
    { name: "hr_presence_state", type: "selection" },
    { name: "name_work_location_display", type: "char" }
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
