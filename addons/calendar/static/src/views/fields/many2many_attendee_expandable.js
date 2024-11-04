import { useState, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { reposition } from "@web/core/position/utils";
import { Many2ManyAttendee, many2ManyAttendee } from "@calendar/views/fields/many2many_attendee";

export class Many2ManyAttendeeExpandable extends Many2ManyAttendee {
    static template = "calendar.Many2ManyAttendeeExpandable";
    state = useState({ expanded: false });

    setup() {
        super.setup();
        this.attendeesCount = this.props.record.data.attendees_count;
        this.acceptedCount = this.props.record.data.accepted_count;
        this.declinedCount = this.props.record.data.declined_count;
        this.uncertainCount = this.attendeesCount - this.acceptedCount - this.declinedCount;

        if (!this.env.isSmall) {
            useEffect(
                () => {
                    const popover = document
                        .querySelector(".o_field_many2manyattendeeexpandable")
                        .closest(".o_popover");
                    const target = document.querySelector(
                        `.fc-event[data-event-id="${this.props.record.resId}"]`
                    );
                    reposition(popover, target, { position: "right", margin: 0 });
                },
                () => [this.state.expanded]
            );
        }
    }

    onExpanderClick() {
        this.state.expanded = !this.state.expanded;
    }
}

export const many2ManyAttendeeExpandable = {
    ...many2ManyAttendee,
    component: Many2ManyAttendeeExpandable,
};

registry.category("fields").add("many2manyattendeeexpandable", many2ManyAttendeeExpandable);
