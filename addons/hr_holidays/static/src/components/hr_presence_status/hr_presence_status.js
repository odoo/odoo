import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { HrPresenceStatus, hrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";
import { HrPresenceStatusPrivate, hrPresenceStatusPrivate } from "@hr/components/hr_presence_status_private/hr_presence_status_private";
import {
    HrPresenceStatusPill,
    hrPresenceStatusPill,
} from "@hr/components/hr_presence_status_pill/hr_presence_status_pill";
import {
    HrPresenceStatusPrivatePill,
    hrPresenceStatusPrivatePill,
} from "@hr/components/hr_presence_status_private_pill/hr_presence_status_private_pill";

const patchHrPresenceStatus = () => ({

    get label() {
        if (this.value.includes("holiday")) {
            return _t("%(label)s, back on %(date)s",
                {
                    label: super.label,
                    date: this.props.record.data['leave_date_to'].toLocaleString(
                        {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                        }
                    )
                }
            )
        }
        return super.label
    },

    get icon() {
        if (this.value.startsWith("presence_holiday")) {
            return "fa-plane";
        }
        return super.icon;
    },

    get color() {
        if (this.value.startsWith("presence_holiday")) {
            return `${this.value === "presence_holiday_present" ? "text-success" : "o_icon_employee_absent"}`;
        }
        return super.color;
    },
});

const patchHrPresenceStatusPill = () => ({
    get color() {
        if (this.value.startsWith("presence_holiday")) {
            return this.value === "presence_holiday_present"
                ? "btn-outline-success"
                : "btn-outline-warning";
        }
        return super.color;
    },
});

// Applies common patch on both components
patch(HrPresenceStatus.prototype, patchHrPresenceStatus());
patch(HrPresenceStatusPrivate.prototype, patchHrPresenceStatus());

// Applies patch on one component and the other should be affected also, since it's extended from it.
patch(HrPresenceStatusPill.prototype, patchHrPresenceStatusPill());

const patchHrPresenceStatusPrivate = () => ({
    get label() {
        if (this.props.record.data.current_leave_id){
            let label = this.props.record.data.current_leave_id.display_name;
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
// Applies patch to hr_presence_status_private to display the time off type instead of default label
patch(HrPresenceStatusPrivate.prototype, patchHrPresenceStatusPrivate());
patch(HrPresenceStatusPrivatePill.prototype, patchHrPresenceStatusPrivate());

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
        { name: "current_leave_id", type:"many2one"},
    ],
});

Object.assign(hrPresenceStatusPill, {
    fieldDependencies: [
        ...hrPresenceStatusPill.fieldDependencies,
        { name: "leave_date_to", type: "date" },
    ],
});

Object.assign(hrPresenceStatusPrivatePill, {
    fieldDependencies: [
        ...hrPresenceStatusPrivatePill.fieldDependencies,
        ...hrPresenceStatusPill.fieldDependencies,
        { name: "current_leave_id", type: "many2one" },
    ],
});
