import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";
import { renderToFragment } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class AttendeeCalendarCommonRenderer extends CalendarCommonRenderer {
    static activityTemplate = "calendar.AttendeeCalendarCommonRenderer.activity";
    static eventTemplate = "calendar.AttendeeCalendarCommonRenderer.event";
    static components = {
        ...CalendarCommonRenderer.components,
        Popover: AttendeeCalendarCommonPopover,
    };

    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        this.orm = useService("orm");
    }

    /**
     * Make sure the activities are set before any other event.
     */
    get options() {
        const defaultEventOrder = "start,-duration,allDay,title"; // (cf full calendar library BASE_OPTION_DEFAULTS)
        return {
            ...super.options,
            eventOrder: "isActivity," + defaultEventOrder,
        };
    }

    /**
     * @override
     *
     * Give a new key to our fc records to be able to iterate through in templates
     */
    convertRecordToEvent(record) {
        let editable = false;
        if (record && !record.isActivity && record.rawRecord) {
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
        if (event.extendedProps.isActivity) {
            const record = this.props.model.activities[event.id];
            return record
                ? ["o_activity_event", "o_event_allday", `o_calendar_color_${record.colorIndex}`]
                : [];
        }
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
     * Map model records to full calendar library events.
     * Handling both "calendar.event" and "mail.activity" records as events.
     */
    mapRecordsToEvents() {
        let events = super.mapRecordsToEvents();
        if (this.props.model.showActivities) {
            const activityEvents = Object.values(this.props.model.data.activities).map((r) => {
                const event = this.convertRecordToEvent(r);
                return {
                    ...event,
                    isActivity: true,
                };
            });
            events = events.concat(activityEvents);
        }
        return events;
    }

    /**
     * Mark activity event related mail.activity as done.
     */
    async onActivityMarkedDone(ev) {
        const activityId = parseInt(ev.target.dataset.activityId);
        if (!activityId) {
            return;
        }
        await this.orm.call("mail.activity", "action_done", [[activityId]]);
        this.notification.add(_t("Activity successfully marked as done."), {
            type: "success",
        });
        await this.props.model.debouncedLoad();
    }

    onClick(info) {
        if (info.event.extendedProps.isActivity) {
            this.openActivityPopover(info);
            return;
        }
        super.onClick(info);
    }

    onDblClick(info) {
        if (info.event.extendedProps.isActivity) {
            this.openActivityPopover(info);
            return;
        }
        super.onDblClick(info);
    }

    /**
     * Render activity events with a custom template.
     */
    onEventContent(arg) {
        const { event } = arg;
        if (event.extendedProps.isActivity) {
            const activityEvent = this.props.model.activities[event.id];
            if (activityEvent) {
                const fragment = renderToFragment(this.constructor.activityTemplate, {
                    ...activityEvent,
                    startTime: this.getStartTime(activityEvent),
                    endTime: this.getEndTime(activityEvent),
                    onActivityMarkedDone: this.onActivityMarkedDone.bind(this),
                });
                return { domNodes: fragment.children };
            }
            return true;
        }
        return super.onEventContent(arg);
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

    openActivityPopover(info) {
        return; // todo
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
