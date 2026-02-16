import { AttendeeCalendarActivityListPopover } from "@calendar/views/attendee_calendar/activity/attendee_calendar_activity_list_popover";
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
        this.activityListPopover = useCalendarPopover(AttendeeCalendarActivityListPopover);
    },

    /**
     * @override
     * Make sure the activities are set before any other event.
     */
    get options() {
        const defaultEventOrder = "start,-duration,allDay,title"; // (cf full calendar library BASE_OPTION_DEFAULTS)
        return {
            ...super.options,
            eventOrder: "isActivity," + defaultEventOrder,
        };
    },

    /**
     * @override
     */
    eventClassNames({ el, event }) {
        if (event.extendedProps?.isActivity) {
            const record = this.props.model.activities[event.id];
            if (!record) {
                return [];
            }
            const classesToAdd = [
                "o_activity_event",
                "o_event_allday",
                `o_calendar_color_${record.colorIndex}`,
            ];
            return classesToAdd;
        }
        return super.eventClassNames({ el, event });
    },

    /**
     * @override
     * Adding activity events to the displayed Full Calendar events.
     */
    mapRecordsToEvents() {
        let events = super.mapRecordsToEvents();
        if (this.props.model.showActivities) {
            const activityEvents = Object.values(this.props.model.activities).map((r) => {
                const event = this.convertRecordToEvent(r);
                return {
                    ...event,
                    editable: false, // (no drag & drop, no time extension, ...)
                    isActivity: true,
                };
            });
            events = events.concat(activityEvents);
        }
        return events;
    },

    /**
     * @override
     * Open activity list popover on click.
     */
    onClick(info) {
        if (info.event.extendedProps?.isActivity) {
            this.openActivityListPopover(info);
            return;
        }
        super.onClick(info);
    },

    /**
     * @override
     * Do not handle double clicks for activities.
     */
    onDblClick(info) {
        if (info.event.extendedProps?.isActivity) {
            return;
        }
        super.onDblClick(info);
    },

    /**
     * @override
     * Render activity events with a custom template.
     */
    onEventContent(arg) {
        const { event } = arg;
        if (event.extendedProps?.isActivity) {
            const activityEvent = this.props.model.activities[event.id];
            if (activityEvent) {
                const fragment = renderToFragment(this.constructor.activityTemplate, activityEvent);
                return { domNodes: fragment.children };
            }
            return true;
        }
        return super.onEventContent(arg);
    },

    /**
     * Open the activity list popover for a specific date.
     */
    openActivityListPopover(info) {
        const activityEvent = this.props.model.activities[info.event.id];
        this.activityListPopover.open(
            info.el,
            {
                activityIds: activityEvent.rawRecord.map((a) => a.id),
                model: this.props.model,
                onActivityChanged: () => {
                    this.props.model.load();
                },
            },
            `o_cw_popover o_cw_activity_popover card o_calendar_color_${activityEvent.colorIndex}`
        );
    },
});
