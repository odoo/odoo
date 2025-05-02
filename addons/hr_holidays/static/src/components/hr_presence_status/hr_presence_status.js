import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { HrPresenceStatus, hrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";
import { HrPresenceStatusPrivate, hrPresenceStatusPrivate } from "@hr/components/hr_presence_status_private/hr_presence_status_private";

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

// Applies common patch on both components
patch(HrPresenceStatus.prototype, patchHrPresenceStatus());
patch(HrPresenceStatusPrivate.prototype, patchHrPresenceStatus());

// Applies patch to hr_presence_status_private to display the time off type instead of default label
patch(HrPresenceStatusPrivate.prototype, {
    get label() {
        return this.props.record.data.current_leave_id
            ? this.props.record.data.current_leave_id.display_name + _t(", back on ") + this.props.record.data['leave_date_to'].toLocaleString(
                {
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric',
                }
            )
            : super.label;
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
        { name: "current_leave_id", type:"many2one"},
    ],
});
