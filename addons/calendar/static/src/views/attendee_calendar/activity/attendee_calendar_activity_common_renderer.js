import { AttendeeCalendarActivityPopover } from "@calendar/views/attendee_calendar/activity/attendee_calendar_activity_popover";
import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
import { patch } from "@web/core/utils/patch";
import { renderToFragment } from "@web/core/utils/render";
import { useCalendarPopover } from "@web/views/calendar/hooks/calendar_popover_hook";
import { useService } from "@web/core/utils/hooks";

/**
 * Render the pending user activities in the Attendee Calendar day, week and month views.
 *
 * Done using a patch to prevent loading this feature and its mail components/store service in POS
 * (only POS module concerned/using the attendee calendar view : 'pos_appointment').
 */
patch(AttendeeCalendarCommonRenderer, {
    activityTemplate: "calendar.AttendeeCalendarCommonRenderer.activity",
});
patch(AttendeeCalendarCommonRenderer.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.activityPopover = useCalendarPopover(AttendeeCalendarActivityPopover);
    },

    /**
     * @override
     * Make sure the activity events are set after any other event.
     */
    get options() {
        const defaultEventOrder = "start,-duration,allDay,title"; // (cf full calendar library BASE_OPTION_DEFAULTS)
        return {
            ...super.options,
            eventOrder: "-isActivity," + defaultEventOrder,
        };
    },

    /**
     * @override
     */
    eventClassNames({ el, event }) {
        if (!event.extendedProps?.isActivity) {
            return super.eventClassNames({ el, event });
        }
        const record = this.props.model.activityEvents[event.id];
        return [
            "o_event",
            "o_activity_event",
            "o_event_allday",
            ...(record ? [`o_calendar_color_${record.colorIndex}`] : []),
        ];
    },

    /**
     * @override
     * Adding activity events to the displayed Full Calendar events.
     */
    mapRecordsToEvents() {
        const events = super.mapRecordsToEvents();
        if (!this.props.model.showActivities) {
            return events;
        }
        const activityEvents = Object.values(this.props.model.activityEvents).map((r) => {
            const event = this.convertRecordToEvent(r);
            return {
                ...event,
                editable: false, // (no drag & drop, no time extension, ...)
                isActivity: true,
            };
        });
        return events.concat(activityEvents);
    },

    /**
     * @override
     * Open activity list popover on event click.
     */
    onClick(info) {
        const activityEvent = info.event.extendedProps?.isActivity
            ? this.props.model.activityEvents[info.event.id]
            : false;
        if (!activityEvent) {
            return super.onClick(info);
        }
        this.activityPopover.open(
            info.el,
            {
                model: this.props.model,
                record: activityEvent,
                activity: this.env.services["mail.store"]["mail.activity"].get(
                    activityEvent.activityId
                ),
                onViewMeeting: (eventId) => {
                    this.activityPopover.close();
                    const el = document.querySelector(`.fc-event[data-event-id="${eventId}"]`);
                    const record = this.props.model.records[eventId];
                    if (el && record) {
                        this.fc.api.scrollToTime(record.start);
                        this.openPopover(el, record);
                    }
                },
            },
            `o_cw_popover o_cw_activity_popover card o_calendar_color_${activityEvent.colorIndex}`
        );
    },

    /**
     * @override
     * Do not handle double clicks for activity events.
     */
    onDblClick(info) {
        if (!info.event.extendedProps?.isActivity) {
            super.onDblClick(info);
        }
    },

    /**
     * @override
     * Render activity events with a custom template.
     */
    onEventContent(arg) {
        const { event } = arg;
        if (!event.extendedProps?.isActivity) {
            return super.onEventContent(arg);
        }
        const activityEvent = this.props.model.activityEvents[event.id];
        if (activityEvent) {
            const fragment = renderToFragment(this.constructor.activityTemplate, activityEvent);
            return { domNodes: fragment.children };
        }
        return true;
    },
});
