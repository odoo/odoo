import { registry } from "@web/core/registry";
import { HrPresenceStatus, hrPresenceStatus } from "../hr_presence_status/hr_presence_status";

export class HrPresenceStatusPrivate extends HrPresenceStatus { }

export const hrPresenceStatusPrivate = {
    ...hrPresenceStatus,
    component: HrPresenceStatusPrivate,
};

registry.category("fields").add("hr_presence_status_private", hrPresenceStatusPrivate);
