import { Component, useEffect, useRef } from "@odoo/owl";

export class CalendarScheduleSection extends Component {
    static template = "web.CalendarScheduleSection";
    static props = {
        model: Object,
        editRecord: Function,
    };
    setup() {
        this.rootRef = useRef("eventsToSchedule");
        useEffect(
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

    openRecord(event) {
        this.props.editRecord({ ...event, title: event.name });
    }
}
