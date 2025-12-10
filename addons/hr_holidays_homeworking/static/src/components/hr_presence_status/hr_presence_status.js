import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { HrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";
import { HrPresenceStatusPrivate } from "@hr/components/hr_presence_status_private/hr_presence_status_private";
import { HrPresenceStatusPill } from "@hr/components/hr_presence_status_pill/hr_presence_status_pill";
import { HrPresenceStatusPrivatePill } from "@hr/components/hr_presence_status_private_pill/hr_presence_status_private_pill";

const patchHrPresenceStatus = () => ({
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

    get label() {
        if (this.value?.includes("holiday")) {
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
        return super.label;
    },
});

patch(HrPresenceStatus.prototype, patchHrPresenceStatus());
patch(HrPresenceStatusPrivate.prototype, patchHrPresenceStatus());

const patchHrPresenceStatusPill = () => ({
    get color() {
        if (this.value?.includes("holiday")) {
            return this.value === "presence_holiday_present"
                ? "btn-outline-success"
                : "btn-outline-warning";
        }
        else if (this.location) {
            let color = "btn-outline-secondary text-muted";
            if (this.props.record.data.hr_presence_state !== "out_of_working_hour") {
                color =
                    this.props.record.data.hr_presence_state === "present"
                        ? "btn-outline-success"
                        : "btn-outline-warning";
            }
            return color;
        }
        return super.color;
    },
});

patch(HrPresenceStatusPill.prototype, patchHrPresenceStatusPill);
patch(HrPresenceStatusPrivatePill.prototype, patchHrPresenceStatusPill);

const patchHrPresenceStatusPrivate = () => ({
    get label() {
        return this.props.record.data.current_leave_id
            ? _t("%(label)s, back on %(date)s",
                {
                    label: this.props.record.data.current_leave_id.display_name,
                    date: this.props.record.data['leave_date_to'].toLocaleString(
                        {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                        }
                    )
                }
            )
            : super.label;
    }
});

patch(HrPresenceStatusPrivate.prototype, patchHrPresenceStatusPrivate());
patch(HrPresenceStatusPrivatePill.prototype, patchHrPresenceStatusPrivate());
