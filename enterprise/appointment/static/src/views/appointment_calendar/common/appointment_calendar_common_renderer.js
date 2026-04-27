/** @odoo-module **/

import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
import { patch } from "@web/core/utils/patch";
import { useAppointmentRendererHook } from "@appointment/views/appointment_calendar/hooks";

patch(AttendeeCalendarCommonRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        const fns = useAppointmentRendererHook(
            () => [this.fc.el],
        );
        Object.assign(this, fns);
    },

    get options() {
        const options = super.options;
        if (this.getEventTimeFormat) {
            options.eventTimeFormat = this.getEventTimeFormat();
        }
        options.eventAllow = this.onEventAllow;
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
     * @overrde
     */
    onEventClick(info) {
        if (!this.isSlotCreationMode()) {
            return super.onEventClick(...arguments);
        }
        info.jsEvent.preventDefault();
        info.jsEvent.stopPropagation();
        if (info.event.extendedProps.slotId) {
            info.event.remove();
            this.props.model.removeSlot(info.event.extendedProps.slotId);
        }
    },

    /**
     * @override
     */
    eventClassNames({ event }) {
        const classesToAdd = super.eventClassNames(...arguments);
        if (event.extendedProps.slotId) {
            classesToAdd.push("o_calendar_slot");
        }
        return classesToAdd;
    },

    /**
     * @override
     */
    onEventDidMount(info) {
        super.onEventDidMount(...arguments);
        const { el, event } = info;
        if (event.extendedProps.slotId) {
            const bg = el.querySelector(".fc-event-main");
            if (bg) {
                const duration = (event.end - event.start) / 3600000;
                const iconSize = duration < 1 || event.allDay || this.props.model.scale === "month" ? "" : "fa-2x";
                const domParser = new DOMParser();
                const injectedContentEl = domParser.parseFromString(
                    /* xml */ `
                    <div class="fc-bg position-absolute top-0 end-0 bottom-0 start-0 o_calendar_slot_delete">
                        <button class="close btn d-flex align-items-center justify-content-center w-100 h-100 m-0 border-0 p-0 bg-success bg-opacity-50 o_hidden">
                            <i class='fa fa-trash ${iconSize}'></i>
                        </button>
                    </div>
                `,
                    "text/html"
                ).body.firstChild;
                bg.insertAdjacentElement("afterend", injectedContentEl);
            }
        }
    },

    /**
     * @override
     */
    isSelectionAllowed(event) {
        let result = super.isSelectionAllowed(...arguments);
        if (this.isSlotCreationMode()) {
            result = result && luxon.DateTime.fromJSDate(event.start) > luxon.DateTime.now();
        }
        return result;
    },

    /**
     * @override
     */
    async onSelect(info) {
        info.jsEvent.preventDefault();
        if (!this.isSlotCreationMode()) {
            return super.onSelect(...arguments);
        }
        this.props.model.createSlot(this.fcEventToRecord(info));
        this.fc.api.unselect();
    },

    /**
     * @override
     */
    onDateClick(info) {
        if (info.jsEvent.defaultPrevented) {
            return;
        }
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
        this.props.model.createSlot(this.fcEventToRecord(info));
    },

    /**
     * @override
     */
    onEventDrop(info) {
        if (!this.isSlotCreationMode()) {
            return super.onEventDrop(...arguments);
        }
        this.props.model.updateSlot(this.fcEventToRecord(info.event));
    },

    /**
     * @override
     */
    onEventResize(info) {
        if (!this.isSlotCreationMode()) {
            return super.onEventResize(...arguments);
        }
        this.props.model.updateSlot(this.fcEventToRecord(info.event));
    },

    /**
     * @override
     */
    onEventDragStart(info) {
        if (!this.isSlotCreationMode()) {
            return super.onEventDragStart(...arguments);
        }
    },

    /**
     * @override
     */
    onEventResizeStart(info) {
        if (!this.isSlotCreationMode()) {
            return super.onEventResizeStart(...arguments);
        }
    },

    /**
     * @override
     */
    onEventMouseEnter(info) {
        if (!this.isSlotCreationMode()) {
            return super.onEventMouseEnter(...arguments);
        }
        const buttonEl = info.el.querySelector(".fc-bg > button");
        buttonEl && buttonEl.classList.remove("o_hidden");
    },

    /**
     * @override
     */
    onEventMouseLeave(info) {
        if (!this.isSlotCreationMode()) {
            return super.onEventMouseLeave(...arguments);
        }
        const buttonEl = info.el.querySelector(".fc-bg > button");
        buttonEl && buttonEl.classList.add("o_hidden");
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
