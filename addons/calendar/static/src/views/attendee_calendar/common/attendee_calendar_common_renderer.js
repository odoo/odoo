import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";

export class AttendeeCalendarCommonRenderer extends CalendarCommonRenderer {
    static eventTemplate = "calendar.AttendeeCalendarCommonRenderer.event";
    static components = {
        ...CalendarCommonRenderer.components,
        Popover: AttendeeCalendarCommonPopover,
    };

    get interactiveOptions() {
        return {
            ...super.interactiveOptions,
            moreLinkClick: () => {
                this.toggleDayGridFoldButton();
                // do not let fullcalendar open its default "more" popover.
                return true;
            },
        };
    }

    get options() {
        return {
            ...super.options,
            eventsSet: this.onEventsSet,
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
     * Toggle the visibility of the day grid fold/unfold button.
     * Only visible if the event limit is exceeded.
     */
    onEventsSet(events) {
        if (!this.dayGridFoldButton) {
            return;
        }
        // Check if the event limit is exceeded.
        // i.e. if at least one day cell contains an event count exceeding the event limit.
        const counts = {};
        const limitExceeded = events.some(
            (e) =>
                e.allDay &&
                (counts[e.startStr] = (counts[e.startStr] || 0) + 1) > this.props.model.eventLimit
        );
        // Show button if the event limit is exceeded, hide it otherwise.
        this.dayGridFoldButton.classList.toggle("d-none", !limitExceeded);
        this.dayGridFoldButton.classList.toggle("d-flex", limitExceeded);
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
    onEventDidMount({ el, event }) {
        super.onEventDidMount(...arguments);
        const record = this.props.model.records[event.id];
        if (record) {
            if (this.env.searchModel?.context?.default_calendar_event_id === parseInt(event.id)) {
                this.openPopover(el, record);
            }
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

    /**
     * Fold/unfold the all day events in the day grid.
     */
    toggleDayGridFoldButton() {
        if (!this.dayGridFoldButton) {
            return;
        }
        if (this.fc.api.getOption("dayMaxEventRows") !== this.props.model.eventLimit) {
            // Fold: only display events up to event limit.
            this.fc.api.setOption("dayMaxEventRows", this.props.model.eventLimit);
            this.props.model.currentEventLimit = this.props.model.eventLimit;
            this.dayGridFoldButton.classList.replace("oi-chevron-up", "oi-chevron-down");
        } else {
            // Unfold: display every events.
            this.fc.api.setOption("dayMaxEventRows", false);
            this.props.model.currentEventLimit = false;
            this.dayGridFoldButton.classList.replace("oi-chevron-down", "oi-chevron-up");
        }
    }

    /**
     * @override
     * Render a button to fold/unfold the all day events in the day grid.
     */
    viewDidMount({ el, view }) {
        super.viewDidMount({ el, view });
        if (["day", "week"].includes(this.props.model.scale)) {
            const box = el.querySelector(".fc-scroller-harness:has(.fc-daygrid-body)");
            if (!box) {
                return;
            }
            // Restore previous day grid fold/unfold state
            const eventLimit = this.props.model.currentEventLimit ?? this.props.model.eventLimit;
            this.fc.api.setOption("dayMaxEventRows", eventLimit);
            // Render fold/unfold button (hidden by default, visibility handled in onEventsSet)
            const button = document.createElement("button");
            button.className =
                "o_calendar_daygrid_fold_btn position-absolute top-0 bottom-0 z-2 " +
                "btn oi opacity-75 opacity-100-hover border-0 d-none align-items-start justify-content-center " +
                `${eventLimit ? "oi-chevron-down" : "oi-chevron-up"}`;
            button.addEventListener("click", this.toggleDayGridFoldButton.bind(this));
            box.insertAdjacentElement("beforeend", button);
            this.dayGridFoldButton = button;
        }
    }
}
