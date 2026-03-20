import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { HrPresenceStatus, hrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";
import { HrPresenceStatusPrivate, hrPresenceStatusPrivate } from "@hr/components/hr_presence_status_private/hr_presence_status_private";

const patchHrPresenceStatus = () => ({

    get label() {
        if (this.value.includes("holiday")) {
            return _t("%(label)s, back on %(date)s",
                {
                    label: this.value !== false
                        ? this.options.find(([value, label]) => value === this.value)[1]
                        : "",
                    date: this.props.record.data['leave_date_to'].toLocaleString(
                        {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                        }
                    )
                }
            )
        } else if (this.location) {
            return this.props.record.data.work_location_name || _t("Unspecified")
        }
        return super.label
    },

    get icon() {
        if (this.value?.includes("holiday")) {
            return "fa-plane";
        } else if (this.location) {
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

    get color() {
        if (this.value?.includes("holiday")) {
            return `${this.value === "presence_holiday_present" ? "text-success" : "o_icon_employee_absent"}`;
        } else if (this.location) {
            let color = "text-muted";
            if (this.props.record.data.hr_presence_state !== "out_of_working_hour") {
                color = this.props.record.data.hr_presence_state === "present" ?  "text-success" : "o_icon_employee_absent";
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
        if (this.props.record.data.current_work_entry_type_id){
            let label = this.props.record.data.current_work_entry_type_id.display_name;
            if (this.props.record.data.leave_date_to) {
                label += _t(", back on ") + this.props.record.data['leave_date_to'].toLocaleString(
                    {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                    }
                )
            }
            return label;
        }
        return super.label;
    }
});

Object.assign(hrPresenceStatus, {
    fieldDependencies: [
        ...hrPresenceStatus.fieldDependencies,
        { name: "leave_date_to", type: "date" },
    ],
});

Object.assign(hrPresenceStatusPrivate, {
    fieldDependencies: [
        ...hrPresenceStatusPrivate.fieldDependencies,
        ...hrPresenceStatus.fieldDependencies,
        { name: "current_work_entry_type_id", type:"many2one"},
    ],
});
