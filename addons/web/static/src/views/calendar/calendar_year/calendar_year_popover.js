// @ts-check

/** @module @web/views/calendar/calendar_year/calendar_year_popover - Popover listing grouped records when clicking a day cell in year view */

import { Component } from "@odoo/owl";
import { formatDate } from "@web/core/l10n/dates";
import { Dialog } from "@web/ui/dialog/dialog";
import { getColor, getFormattedDateSpan } from "@web/views/calendar/calendar_utils";

/** Popover shown when clicking a day cell in year view, listing grouped records. */
export class CalendarYearPopover extends Component {
    static components = { Dialog };
    static template = "web.CalendarYearPopover";
    static subTemplates = {
        popover: "web.CalendarYearPopover.popover",
        body: "web.CalendarYearPopover.body",
        footer: "web.CalendarYearPopover.footer",
        record: "web.CalendarYearPopover.record",
    };
    static props = {
        close: Function,
        date: true,
        model: Object,
        records: Array,
        createRecord: Function,
        deleteRecord: Function,
        editRecord: Function,
    };

    /** @returns {Array<{ title: string, start: Object, end: Object, records: Object[] }>} grouped and sorted records */
    get recordGroups() {
        return this.computeRecordGroups();
    }

    /** @returns {string} formatted date string for the dialog title */
    get dialogTitle() {
        return formatDate(this.props.date, { format: "DDD" });
    }

    /** @returns {Array<{ title: string, start: Object, end: Object, records: Object[] }>} grouped and sorted records */
    computeRecordGroups() {
        const recordGroups = this.groupRecords();
        return this.getSortedRecordGroups(recordGroups);
    }
    /**
     * Group popover records by their formatted date span.
     * @returns {Array<{ title: string, start: Object, end: Object, records: Object[] }>}
     */
    groupRecords() {
        const recordGroups = {};
        for (const record of this.props.records) {
            const start = record.start;
            const end = record.end;

            const duration = end.diff(start, "days").days;
            const modifiedRecord = Object.create(record);
            modifiedRecord.startHour =
                !record.isAllDay && duration < 1 ? start.toFormat("HH:mm") : "";

            const formattedDate = getFormattedDateSpan(start, end);
            if (!(formattedDate in recordGroups)) {
                recordGroups[formattedDate] = {
                    title: formattedDate,
                    start,
                    end,
                    records: [],
                };
            }
            recordGroups[formattedDate].records.push(modifiedRecord);
        }
        return Object.values(recordGroups);
    }
    /**
     * @param {{ colorIndex: number | string }} record - calendar record
     * @returns {string} CSS class for the record color, or empty string
     */
    getRecordClass(record) {
        const { colorIndex } = record;
        const color = getColor(colorIndex);
        if (color && typeof color === "number") {
            return `o_calendar_color_${color}`;
        }
        return "";
    }
    /**
     * @param {{ colorIndex: number | string }} record - calendar record
     * @returns {string} inline CSS style for the record color, or empty string
     */
    getRecordStyle(record) {
        const { colorIndex } = record;
        const color = getColor(colorIndex);
        if (color && typeof color === "string") {
            return `background-color: ${color};`;
        }
        return "";
    }
    /**
     * Sort record groups by start time, with same-day groups first.
     * @param {Array<{ title: string, start: Object, end: Object, records: Object[] }>} recordGroups
     * @returns {Array<{ title: string, start: Object, end: Object, records: Object[] }>} sorted groups
     */
    getSortedRecordGroups(recordGroups) {
        return recordGroups.sort((a, b) => {
            if (a.start.hasSame(a.end, "days")) {
                return Number.MIN_SAFE_INTEGER;
            } else if (b.start.hasSame(b.end, "days")) {
                return Number.MAX_SAFE_INTEGER;
            } else if (a.start.toMillis() - b.start.toMillis() === 0) {
                return a.end.toMillis() - b.end.toMillis();
            }
            return a.start.toMillis() - b.start.toMillis();
        });
    }

    /** Create a new all-day record on the popover's date and close. */
    onCreateButtonClick() {
        this.props.createRecord({
            start: this.props.date,
            isAllDay: true,
        });
        this.props.close();
    }
    /**
     * @param {Object} record - calendar record to edit
     */
    onRecordClick(record) {
        this.props.editRecord(record);
        this.props.close();
    }
}
