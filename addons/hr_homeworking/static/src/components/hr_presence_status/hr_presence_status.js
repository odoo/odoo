/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { HrPresenceStatus, hrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";

patch(HrPresenceStatus.prototype, {
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

    get label() {
        if (this.location) {
            return _t("Working from %s", this.location);
        }
        return super.label;
    },

    get location() {
        let location = this.value?.split("_")[1] || "";
        if (location && !['home', 'office', 'other'].includes(location)) {
            location = "";
        }
        return location;
    },
});

const additionalFieldDependencies = [
    { name: "hr_presence_state", type: "selection" },
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
