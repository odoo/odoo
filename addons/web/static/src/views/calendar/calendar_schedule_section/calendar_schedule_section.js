import { useLayoutEffect } from "@web/owl2/utils";
import { Component, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class CalendarScheduleSection extends Component {
    static template = "web.CalendarScheduleSection";
    static props = {
        model: Object,
        editRecord: Function,
    };
    setup() {
        this.rootRef = useRef("eventsToSchedule");
        this.state = useState({ collapsed: false });
        useLayoutEffect(
            (el) => {
                new FullCalendar.Interaction.Draggable(el, {
                    itemSelector: ".o_event_to_schedule_draggable",
                    eventData: function (el) {
                        return {
                            title: el.innerText,
                            id: el.dataset.resId,
                        };
                    },
                    appendTo: document.body,
                });
            },
            () => [this.rootRef.el]
        );
    }

    get displayLoadMoreButton() {
        const { eventsToSchedule } = this.props.model.data;
        return eventsToSchedule && eventsToSchedule.records.length < eventsToSchedule.length;
    }

    get toScheduleString() {
        const { eventsToSchedule } = this.props.model.data;
        if (eventsToSchedule.length) {
            return _t("%s to schedule", eventsToSchedule.length);
        }
        return _t("Nothing to schedule");
    }

    openRecord(event) {
        this.props.editRecord({ ...event, title: event.name });
    }
}
