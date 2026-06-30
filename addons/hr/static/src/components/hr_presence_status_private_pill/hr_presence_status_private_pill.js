import { registry } from "@web/core/registry";
import {
    HrPresenceStatusPill,
    hrPresenceStatusPill,
} from "../hr_presence_status_pill/hr_presence_status_pill";

export class HrPresenceStatusPrivatePill extends HrPresenceStatusPill {}

export const hrPresenceStatusPrivatePill = {
    ...hrPresenceStatusPill,
    component: HrPresenceStatusPrivatePill,
};

registry.category("fields").add("form.hr_presence_status_private", hrPresenceStatusPrivatePill);
