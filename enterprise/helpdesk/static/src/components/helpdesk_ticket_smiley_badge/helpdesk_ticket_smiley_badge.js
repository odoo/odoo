import { registry } from "@web/core/registry";
import { BadgeField } from "@web/views/fields/badge/badge_field";

export class HelpdeskSmileBadge extends BadgeField {
    static template = "helpdesk.SmileyBadge";
}

export const helpdeskSmileBadge = {
    component: HelpdeskSmileBadge,
};

registry.category("fields").add("helpdesk_smiley_badge", helpdeskSmileBadge);
