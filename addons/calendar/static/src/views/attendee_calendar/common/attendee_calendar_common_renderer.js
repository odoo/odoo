import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { AttendeeCalendarCommonPopover } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_popover";
import { onPatched } from "@odoo/owl";

const { DateTime } = luxon;


export class AttendeeCalendarCommonRenderer extends CalendarCommonRenderer {
    static eventTemplate = "calendar.AttendeeCalendarCommonRenderer.event";
    static headerTemplate = "calendar.AttendeeCalendarCommonRenderer.HeaderTemplate";
    static components = {
        ...CalendarCommonRenderer.components,
        Popover: AttendeeCalendarCommonPopover,
    };

    setup() {
        super.setup(...arguments);
        onPatched(() => {
            // Force to rerender the FC.
            // As it doesn't redraw the header when the event's data changes
            this.fc.api.render();
        });
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
    get options() {
		return {
            ...super.options,
            dayHeaderDidMount: this.onDayHeaderDidMount,
            dayHeaderWillUnmount: this.onDayHeaderWillUnmount,
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

    onDayHeaderEvent(event, date) {
        return;
    }

    onDayHeaderDidMount(info) {
        const date = DateTime.fromJSDate(info.date);
        info.el.addEventListener("click", (ev) => this.onDayHeaderEvent(ev, date));
    }

    onDayHeaderWillUnmount(info) {
        const date = DateTime.fromJSDate(info.date);
        info.el.removeEventListener("click", (ev) => this.onDayHeaderEvent(ev, date));
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
