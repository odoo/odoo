import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import {
    HrPresenceStatus,
    hrPresenceStatus,
} from "@hr/components/hr_presence_status/hr_presence_status";
import {
    HrPresenceStatusPrivate,
    hrPresenceStatusPrivate,
} from "@hr/components/hr_presence_status_private/hr_presence_status_private";

const { DateTime } = luxon;

/**
 * @param {string} label
 * @param {Object} data record data with `leave_datetime_to`
 * @returns {string} the label followed by when the employee is back, in the day of the viewer
 */
function getLabelWithReturn(label, data) {
    const backOn = data.leave_datetime_to;
    if (backOn && backOn.hasSame(DateTime.now(), "day")) {
        return _t("%(label)s, back at %(time)s", {
            label,
            time: backOn.toLocaleString(DateTime.TIME_SIMPLE),
        });
    }
    return _t("%(label)s, back on %(date)s", {
        label,
        date: backOn.toLocaleString({
            day: "numeric",
            month: "short",
            year: "numeric",
        }),
    });
}

const patchHrPresenceStatus = () => ({
    get label() {
        if (this.value.includes("holiday")) {
            return getLabelWithReturn(
                this.value !== false ? this.options.find(([value]) => value === this.value)[1] : "",
                this.props.record.data
            );
        } else if (this.location) {
            return this.props.record.data.work_location_name || _t("Unspecified");
        }
        return super.label;
    },

    get icon() {
        if (this.value?.includes("holiday")) {
            return "travel";
        } else if (this.location) {
            switch (this.location) {
                case "home":
                    return "home";
                case "office":
                    return "business";
                case "other":
                    return "location_on";
            }
        }
        return super.icon;
    },

    get color() {
        if (this.value?.includes("holiday")) {
            return `${
                this.value === "presence_holiday_present"
                    ? "text-success"
                    : "o_icon_employee_absent"
            }`;
        } else if (this.location) {
            let color = "text-muted";
            if (this.props.record.data.hr_presence_state !== "out_of_working_hour") {
                color =
                    this.props.record.data.hr_presence_state === "present"
                        ? "text-success"
                        : "o_icon_employee_absent";
            }
            return color;
        }
        return super.color;
    },
});

// Applies common patch on both components
patch(HrPresenceStatus.prototype, patchHrPresenceStatus());
patch(HrPresenceStatusPrivate.prototype, patchHrPresenceStatus());

// Applies patch on one component and the other should be affected also, since it's extended from it.
patch(HrPresenceStatusPrivate.prototype, {
    get label() {
        if (this.props.record.data.current_work_entry_type_id) {
            let label = this.props.record.data.current_work_entry_type_id.display_name;
            if (this.props.record.data.leave_datetime_to) {
                label = getLabelWithReturn(label, this.props.record.data);
            }
            return label;
        }
        return super.label;
    },
});

Object.assign(hrPresenceStatus, {
    fieldDependencies: [
        ...hrPresenceStatus.fieldDependencies,
        { name: "leave_datetime_to", type: "datetime" },
    ],
});

Object.assign(hrPresenceStatusPrivate, {
    fieldDependencies: [
        ...hrPresenceStatusPrivate.fieldDependencies,
        ...hrPresenceStatus.fieldDependencies,
        { name: "current_work_entry_type_id", type: "many2one" },
    ],
});
