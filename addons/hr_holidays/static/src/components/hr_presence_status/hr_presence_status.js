import { patch } from "@web/core/utils/patch";

import { HrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";
import {
    HrPresenceStatusPrivate,
    hrPresenceStatusPrivate,
} from "@hr/components/hr_presence_status_private/hr_presence_status_private";

const patchHrPresenceStatus = () => ({
    get icon() {
        if (
            this.status &&
            (this.status.startsWith("presence_holiday") || this.status.startsWith("leave_"))
        ) {
            return "fa-plane";
        }
        return super.icon;
    },

    get color() {
        if (this.status && this.status.startsWith("presence_holiday")) {
            return `${
                this.value === "presence_holiday_present"
                    ? "text-success"
                    : "o_icon_employee_absent"
            }`;
        } else if (this.status && this.status?.startsWith("leave_")) {
            switch (this.status) {
                case "leave_online":
                    return "text-success";
                case "leave_away":
                    return "text-warning";
                case "leave_offline":
                    return "text-700";
            }
        }
        return super.color;
    },
});

// Applies common patch on both components
patch(HrPresenceStatus.prototype, patchHrPresenceStatus());
patch(HrPresenceStatusPrivate.prototype, patchHrPresenceStatus());

// Applies patch to hr_presence_status_private to display the time off type instead of default label
patch(HrPresenceStatusPrivate.prototype, {
    get label() {
        return this.props.record.data.current_leave_id
            ? this.props.record.data.current_leave_id[1]
            : super.label;
    },
});

Object.assign(hrPresenceStatusPrivate, {
    fieldDependencies: [
        ...(hrPresenceStatusPrivate.fieldDependencies || []),
        { name: "current_leave_id", type: "many2one" },
    ],
});
