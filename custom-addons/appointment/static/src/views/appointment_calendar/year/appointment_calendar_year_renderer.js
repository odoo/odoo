/** @odoo-module **/

import { AttendeeCalendarYearRenderer } from "@calendar/views/attendee_calendar/year/attendee_calendar_year_renderer";
import { patch } from "@web/core/utils/patch";
import { useAppointmentRendererHook } from "@appointment/views/appointment_calendar/hooks";

patch(AttendeeCalendarYearRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        const fns = useAppointmentRendererHook(() => Object.values(this.fcs).map((fc) => fc.el));
        Object.assign(this, fns);
    },

    get options() {
        const options = super.options;
        if (this.getEventTimeFormat) {
            options.eventTimeFormat = this.getEventTimeFormat();
        }
        options.eventAllow = this.onEventAllow;
        options.selectAllow = this.isSelectionAllowed;
        return options;
    },

    /**
     * @override
     */
    mapRecordsToEvents() {
        this.maxResId = Math.max(Object.keys(this.props.model.data.records).map((id) => Number.parseInt(id)));
        const res = [
            ...super.mapRecordsToEvents(...arguments),
            ...Object.values(this.props.model.data.slots).map((r) => this.convertSlotToEvent(r)),
        ];
        return res;
    },

    /**
     * @override
     */
    convertSlotToEvent(record) {
        const result = {
            ...this.convertRecordToEvent(record),
            id: this.maxResId + record.id, // Arbitrary id to avoid duplicated ids.
            slotId: record.id,
            color: "green",
        };
        result.editable = true; // Keep slots editable
        return result;
    },

    /**
     * @override
     */
    fcEventToRecord(event) {
        if (!event.extendedProps || !event.extendedProps.slotId) {
            return super.fcEventToRecord(...arguments);
        }
        return {
            ...super.fcEventToRecord({
                allDay: event.allDay,
                date: event.date,
                start: event.start,
                end: event.end,
            }),
            slotId: event.extendedProps.slotId,
        };
    },

    /**
     * @override
     */
    onEventRender(info) {
        super.onEventRender(...arguments);
        const { el, event } = info;
        if (event.extendedProps.slotId) {
            el.classList.add("o_calendar_slot");
            const bg = el.querySelector(".fc-bg");
            if (bg) {
                const duration = (event.end - event.start) / 3600000;
                const iconSize = duration < 1 || event.allDay || this.props.model.scale === "month" ? "" : "h1";
                const domParser = new DOMParser();
                const injectedContentEl = domParser.parseFromString(
                    /* xml */ `
                    <button class="close w-100 h-100 disabled o_hidden">
                        <i class='fa fa-trash text-white m-0 ${iconSize}'></i>
                    </button>
                `,
                    "text/html"
                ).body.firstChild;
                bg.appendChild(injectedContentEl);
            }
        }
    },

    findMatchingSlot(start, end = undefined) {
        let predicate;
        if (end) {
            predicate = (slot) => (slot.start.equals(start) && slot.end.equals(end));
        } else {
            predicate = (slot) => (slot.start.equals(start));
        }
        return Object.values(this.props.model.data.slots).find(predicate);
    },

    /**
     * @override
     */
    async onSelect(info) {
        if (!this.isSlotCreationMode()) {
            return super.onSelect(...arguments);
        }
        const start = luxon.DateTime.fromISO(info.startStr);
        const end = luxon.DateTime.fromISO(info.endStr).minus({ days: 1 });
        // 1 day events are handled by onDateClick
        if (start === end) {
            this.unselect();
            return;
        }
        const existingSlot = this.findMatchingSlot(start, end);
        if (existingSlot) {
            this.props.model.removeSlot(existingSlot.id);
        } else {
            this.props.model.createSlot({
                start,
                end,
                isAllDay: true,
            });
        }
        this.unselect();
    },

    /**
     * @override
     */
    onDateClick(info) {
        if (!this.isSlotCreationMode()) {
            return super.onDateClick(...arguments);
        }
        // Disabled in month view
        if (this.props.model.scale === "month") {
            return;
        }
        const date = luxon.DateTime.fromISO(info.dateStr);
        if (date < luxon.DateTime.now()) {
            return;
        }
        const existingSlot = this.findMatchingSlot(date);
        if (existingSlot) {
            this.props.model.removeSlot(existingSlot.id);
        } else {
            this.props.model.createSlot({
                start: luxon.DateTime.fromISO(info.dateStr),
                isAllDay: true,
            });
        }
    },

    /**
     * @override
     */
    isSelectionAllowed(event) {
        if (!this.isSlotCreationMode) {
            return super.isSelectionAllowed?.(...arguments) || true;
        }
        return luxon.DateTime.fromJSDate(event.start) > luxon.DateTime.now();
    },

    /**
     * Prevent drag & drop events in the past in slot creationmode
     */
    onEventAllow(dropInfo, draggedEvent) {
        if (!this.isSlotCreationMode()) {
            return super.onEventAllow?.(...arguments) || true;
        }
        return draggedEvent.extendedProps.slotId && luxon.DateTime.fromJSDate(dropInfo.start) > luxon.DateTime.now();
    },
});
