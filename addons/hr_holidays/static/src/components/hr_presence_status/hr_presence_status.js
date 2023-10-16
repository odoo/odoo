/** @odoo-module **/

import { patch } from "@web/core/utils/patch";

import { HrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";

patch(HrPresenceStatus.prototype, {
    get icon() {
        if (this.value.startsWith("presence_holiday")) {
            return "fa-plane";
        }
        return super.icon;
    },

    get color() {
        if (this.value.startsWith("presence_holiday")) {
            return `text-${this.value === "presence_holiday_present" ? "success" : "warning"}`;
        }
        return super.color;
    },
});
