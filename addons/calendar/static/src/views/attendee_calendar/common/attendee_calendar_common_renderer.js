import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";

export class AttendeeCalendarCommonRenderer extends CalendarCommonRenderer {
    static eventTemplate = "calendar.AttendeeCalendarCommonRenderer.event";
    static components = {
        ...CalendarCommonRenderer.components,
        Popover: AttendeeCalendarCommonPopover,
    };

    /**
     * @override
     * 
     * In month view, do not limit the number of displayed events using a fixed event limit.
     * Instead, explicitly set the "dayMaxEventRows" to "true" to dynamically limit the number
     * of displayed events depending on the available day cell height.
     * Each day cell will have the same height, evenly distributed across the calendar’s total height.
     */
    get interactiveOptions() {
        return {
            ...super.interactiveOptions,
            dayMaxEventRows: this.props.model.scale === "month" ? true : this.props.model.eventLimit,
        };
    }

    /**
     * @override
     *
     * Give a new key to our fc records to be able to iterate through in templates
     */
    convertRecordToEvent(record) {
        let editable = false;
        if (record && record.rawRecord) {
            editable = record.rawRecord.user_can_edit;
        }
        return {
            ...super.convertRecordToEvent(record),
            id: record._recordId || record.id,
            editable: editable,
        };
    }

    /**
     * @override
     */
    eventClassNames({ el, event }) {
        const classesToAdd = super.eventClassNames(...arguments);
        const record = this.props.model.records[event.id];
        if (record) {
            if (record.rawRecord.is_highlighted) {
                classesToAdd.push("o_event_highlight");
            }
            if (record.isAlone) {
                classesToAdd.push("o_attendee_status_alone");
            } else {
                classesToAdd.push(`o_attendee_status_${record.attendeeStatus}`);
            }
        }
        return classesToAdd;
    }

    /**
     * @override
     * In the calendar.event calendar view, when using a single click, we want to create
     * a meeting at the time of the click target, rounded down to closest half hour.
     *
     * By default, the fullcalendar parameter that defines this precision is snapDuration
     * and is 15 min. We cannot modify it directly, as it also defines the time precision
     * of meeting drag and drop, as well as the one of meeting creation between two targets
     * (on click then on release), both of which we want to keep at 15 minutes.
     */
    fcEventToRecord(event) {
        const res = super.fcEventToRecord(...arguments);
        const { id, allDay, end } = event;

        if (!id && !allDay && !end && ["day", "week"].includes(this.props.model.scale)) {
            if (res.start?.minute === 15 || res.start?.minute === 45) {
                res.start = res.start.set({
                    minute: res.start.minute - 15
                });
            }
        }
        return res;
    }

    /**
     * @override
     */
    isEventToFade(event) {
        return super.isEventToFade(...arguments) || event.rawRecord.is_draft;
    }

    /**
     * @override
     * On event mounted, open popover if 'default_calendar_event_id' is specified in the context,
     * if the popover is not already opened and if the event is not being dragged.
     */
    onEventDidMount({ el, event }) {
        super.onEventDidMount(...arguments);
        const record = this.props.model.records[event.id];
        if (
            record &&
            this.env.searchModel?.context?.default_calendar_event_id === parseInt(event.id) &&
            !this.popover.isOpen &&
            !el.classList.contains('fc-event-dragging')
        ) {
            this.openPopover(el, record);
        }
    }

    /**
     * @override
     *
     * Allow slots to be selected over multiple days
     */
    isSelectionAllowed(event) {
        return true;
    }
}
