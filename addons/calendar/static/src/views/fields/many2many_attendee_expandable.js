/** @odoo-module **/

import { useState, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { reposition } from "@web/core/position_hook";
import {
    Many2ManyAttendee,
    many2ManyAttendee,
    preloadMany2ManyAttendee,
} from "@calendar/views/fields/many2many_attendee";

export class Many2ManyAttendeeExpandable extends Many2ManyAttendee {
    state = useState({ expanded: false });
    attendeesCount = null;

    setup() {
        this.attendeesCount = this.props.record.data.attendees_count;

        useEffect(() => {
            const popover = document.querySelector(".o_field_many2manyattendeeexpandable")
                .closest(".o_popover");
            const targetElement = document.querySelector(`.fc-event[data-event-id="${this.props.record.resId}"]`);
            reposition(targetElement, popover, { position: "right", margin: 0 });
        }, () => [ this.state.expanded ]);
    }

    onExpanderClick() {
        this.state.expanded = !this.state.expanded;
    }

    get partners() {
        return this.props.record.preloadedData.partner_ids;
    }

    get acceptedCount() {
        return this.partners.filter(p => p.status === 'accepted').length;
    }

    get declinedCount() {
        return this.partners.filter(p => p.status === 'declined').length;
    }

    get uncertainCount() {
        return this.partners.filter(p => p.status !== 'accepted' && p.status !== 'declined').length;
    }
}

Many2ManyAttendeeExpandable.template = "calendar.Many2ManyAttendeeExpandable";

export const many2ManyAttendeeExpandable = {
    ...many2ManyAttendee,
    component: Many2ManyAttendeeExpandable,
};

registry.category("fields").add("many2manyattendeeexpandable", many2ManyAttendeeExpandable);

registry.category("preloadedData").add("many2manyattendeeexpandable", {
    loadOnTypes: ["many2many"],
    preload: preloadMany2ManyAttendee,
});
