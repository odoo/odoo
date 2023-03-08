import { Many2ManyAttendee } from "@calendar/views/fields/many2many_attendee";
import { patch } from "@web/core/utils/patch";
patch(Many2ManyAttendee.prototype, {
    get tags() {
        const tags = super.tags;
        if (this.props.record.data.unavailable_partner_ids) {
            const unavailablePartnerIds = this.props.record.data.unavailable_partner_ids.records;
            for (const tag of tags) {
                if (unavailablePartnerIds.find((partner) => (tag.resId == partner.resId))) {
                    tag.unavailableIcon = true;
                }
            }
        }
        return tags;
    }
})
