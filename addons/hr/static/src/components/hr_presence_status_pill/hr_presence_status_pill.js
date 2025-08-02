import { registry } from "@web/core/registry";
import { HrPresenceStatus, hrPresenceStatus } from "../hr_presence_status/hr_presence_status";

export class HrPresenceStatusPill extends HrPresenceStatus {
    static template = "hr.HrPresenceStatusPill";

    get classNames() {
        const classNames = ["fw-bold"];
        classNames.push(this.color);
        return classNames.join(" ");
    }

    get color() {
        switch (this.value) {
            case "presence_present":
                return "o_hr_presence_status_pill-present";
            case "presence_absent":
                return "o_hr_presence_status_pill-absent";
            case "presence_out_of_working_hour":
            case "presence_archive":
                return "o_hr_presence_status_pill-off-hours";
            default:
                return "";
        }
    }
}

export const hrPresenceStatusPill = {
    ...hrPresenceStatus,
    component: HrPresenceStatusPill,
};

registry.category("fields").add("form.hr_presence_status", hrPresenceStatusPill);
