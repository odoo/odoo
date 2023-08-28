/** @odoo-module **/

import { patch } from "@web/core/utils/patch";

import { HrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";

patch(HrPresenceStatus.prototype, {
    get classNames() {
        const classNames = super.classNames;
        if (this.value.startsWith("presence_holiday")) {
            return `${classNames} fa-plane`;
        }
        return classNames;
    },

    get color() {
        if (this.value.startsWith("presence_holiday")) {
            return `text-${this.value === "presence_holiday_present" ? "success" : "warning"}`;
        }
        return super.color;
    },
});
