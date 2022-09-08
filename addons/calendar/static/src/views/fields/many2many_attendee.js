/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2ManyTagsAvatarField } from "@web/views/fields/many2many_tags_avatar/many2many_tags_avatar_field";

export class Many2ManyAttendee extends Many2ManyTagsAvatarField {
    get tags() {
        const { partner_ids: partnerIds } = this.props.record.preloadedData;
        const tags = super.tags.map((tag) => {
            const partner = partnerIds.find((partner) => tag.resId === partner.id);
            if (partner) {
                tag.className = `o_attendee_border o_attendee_border_${partner.status}`;
            }
            return tag;
        });

        const organizer = partnerIds.find((partner) => partner.is_organizer);
        if (organizer) {
            const orgId = organizer.id;
            // sort elements according to the partner id
            tags.sort((a, b) => {
                const a_org = a.id === orgId;
                return a_org ? -1 : 1;
            });
        }
        return tags;
    }
}

registry.category("fields").add("many2manyattendee", Many2ManyAttendee);
