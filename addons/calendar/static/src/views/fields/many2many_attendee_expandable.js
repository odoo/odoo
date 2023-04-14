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

    setup() {
        this.attendeesCount = this.props.record.data.attendees_count;
        this.acceptedCount = this.props.record.data.accepted_count;
        this.declinedCount = this.props.record.data.declined_count;
        this.uncertainCount = this.attendeesCount - this.acceptedCount - this.declinedCount;

        useEffect(() => {
            const popover = document.querySelector(".o_field_many2manyattendeeexpandable")
                .closest(".o_popover");
            const targetElement = document.querySelector(`.fc-event[data-event-id="${this.props.record.resId}"]`);
            reposition(targetElement, popover, null, { position: "right", margin: 0 });
        }, () => [ this.state.expanded ]);
    }

    onExpanderClick() {
        this.state.expanded = !this.state.expanded;
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
