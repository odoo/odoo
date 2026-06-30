import { registry } from "@web/core/registry";
import { HrPresenceStatus, hrPresenceStatus } from "../hr_presence_status/hr_presence_status";

export class HrPresenceStatusPill extends HrPresenceStatus {
    static template = "hr.HrPresenceStatusPill";

    /** @override */
    get classNames() {
        const classNames = ["fw-bold", "text-center", "btn", "rounded-pill", "cursor-default"];
        classNames.push(this.color);
        return classNames.join(" ");
    }

    /** @override */
    get color() {
        switch (this.value) {
            case "presence_present":
                return "btn-outline-success";
            case "presence_absent":
                return "btn-outline-warning";
            case "presence_out_of_working_hour":
            case "presence_archive":
                return "btn-outline-secondary text-muted";
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
