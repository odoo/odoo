/** @odoo-module native */
import { _t } from "@web/core/translation";
import { patch } from "@web/core/utils/patch";

import { HrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";
import { HrPresenceStatusPrivate } from "@hr/components/hr_presence_status_private/hr_presence_status_private";
import { HrPresenceStatusPill } from "@hr/components/hr_presence_status_pill/hr_presence_status_pill";
import { HrPresenceStatusPrivatePill } from "@hr/components/hr_presence_status_private_pill/hr_presence_status_private_pill";

function onHoliday(component) {
    return Boolean(component.value?.includes("holiday"));
}

// `back on <date>` where a date is known, and the plain label where it is not:
// hr_holidays guards the same field before formatting it, and an employee can be
// flagged absent without an end date having reached this record.
function backOn(component, label) {
    const end = component.props.record.data.leave_date_to;
    if (!end) {
        return label;
    }
    return _t("%(label)s, back on %(date)s", {
        label,
        date: end.toLocaleString({ day: "numeric", month: "short", year: "numeric" }),
    });
}

// Each getter answers ONLY for a holiday and delegates everything else. The
// location branches these used to carry were a verbatim copy of hr_homeworking's,
// which this module is patched on top of, so `super` already answers them -- and
// a copy is how the two come to disagree.
const patchHrPresenceStatus = () => ({
    get color() {
        if (onHoliday(this)) {
            return this.value === "presence_holiday_present"
                ? "text-success"
                : "o_icon_employee_absent";
        }
        return super.color;
    },

    get icon() {
        return onHoliday(this) ? "fa-plane" : super.icon;
    },

    get label() {
        if (!onHoliday(this)) {
            return super.label;
        }
        const option = this.options.find(([value]) => value === this.value);
        return backOn(this, option ? option[1] : "");
    },
});

patch(HrPresenceStatus.prototype, patchHrPresenceStatus());
patch(HrPresenceStatusPrivate.prototype, patchHrPresenceStatus());

const patchHrPresenceStatusPill = () => ({
    get color() {
        if (onHoliday(this)) {
            return this.value === "presence_holiday_present"
                ? "btn-outline-success"
                : "btn-outline-warning";
        }
        return super.color;
    },
});

patch(HrPresenceStatusPill.prototype, patchHrPresenceStatusPill());
patch(HrPresenceStatusPrivatePill.prototype, patchHrPresenceStatusPill());

const patchHrPresenceStatusPrivate = () => ({
    get label() {
        const leave = this.props.record.data.current_leave_id;
        return leave ? backOn(this, leave.display_name) : super.label;
    },
});

patch(HrPresenceStatusPrivate.prototype, patchHrPresenceStatusPrivate());
patch(HrPresenceStatusPrivatePill.prototype, patchHrPresenceStatusPrivate());
