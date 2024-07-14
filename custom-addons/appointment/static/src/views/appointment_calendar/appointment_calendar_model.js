/** @odoo-module **/

import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarModel.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.data.slots = {};
        this.defaultSlotDurationMinutes = 30;
        this.slotId = 1;
    },

    /**
     * @override
     * Properly take into account the duration from the context.
     * Only when the user makes a click on the calendar (when there's no end) or when the end is invalid.
     */
    buildRawRecord(partialRecord, options) {
        if ('default_duration' in this.meta.context) {
            const defaultDuration = this.meta.context.default_duration;
            if (partialRecord.start && (!partialRecord.end || !partialRecord.end.isValid) && !partialRecord.isAllDay) {
                partialRecord.end = partialRecord.start.plus({ hours: defaultDuration });
            }
        }
        return super.buildRawRecord(...arguments);
    },

    processPartialSlotRecord(record) {
        if (!record.end || !record.end.isValid) {
            if (record.isAllDay) {
                record.end = record.start;
            } else {
                record.end = record.start.plus({ minutes: this.defaultSlotDurationMinutes });
            }
        }
        if (!record.isAllDay) {
            record.title = "";
            if (record.start && record.end) {
                const datesInterval = luxon.Interval.fromDateTimes(record.start, record.end);
                this.defaultSlotDurationMinutes = datesInterval.length('minutes');
            }
        } else {
            const isSameDay = record.start.hasSame(record.end, "day");
            if (!isSameDay && record.start.hasSame(record.end, "month")) {
                // Simplify date-range if an event occurs into the same month (eg. "August, 4-5 2019")
                record.title = record.start.toFormat("LLLL d") + "-" + record.end.toFormat("d, y");
            } else {
                record.title = isSameDay
                    ? record.start.toFormat("DDD")
                    : record.start.toFormat("DDD") + " - " + record.end.toFormat("DDD");
            }
        }
    },

    createSlot(record) {
        this.processPartialSlotRecord(record);
        const slotId = this.slotId++;
        this.data.slots[slotId] = {
            id: slotId,
            title: record.title,
            start: record.start,
            end: record.end,
            isAllDay: record.isAllDay,
        };
        this.notify();
        return this.data.slots[slotId];
    },

    updateSlot(eventRecord) {
        this.processPartialSlotRecord(eventRecord);
        const slot = this.data.slots[eventRecord.slotId];
        Object.assign(slot, {
            title: eventRecord.title,
            start: eventRecord.start,
            end: eventRecord.end,
            isAllDay: eventRecord.isAllDay,
        });
        this.notify();
    },

    removeSlot(slotId) {
        delete this.data.slots[slotId];
        this.notify();
    },

    clearSlots() {
        this.data.slots = {};
        this.notify();
    },
});
