/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { formatDate } from "@web/core/l10n/dates";
import { getColor } from "../colors";

import { Component } from "@odoo/owl";

export class CalendarYearPopover extends Component {
    get recordGroups() {
        return this.computeRecordGroups();
    }

    get dialogTitle() {
        return formatDate(this.props.date, { format: "DDD" });
    }

    computeRecordGroups() {
        const recordGroups = this.groupRecords();
        return this.getSortedRecordGroups(recordGroups);
    }
    groupRecords() {
        const recordGroups = {};
        for (const record of this.props.records) {
            const start = record.start;
            const end = record.end;

            const duration = end.diff(start, "days").days;
            const modifiedRecord = Object.create(record);
            modifiedRecord.startHour =
                !record.isAllDay && duration < 1 ? start.toFormat("HH:mm") : "";

            const formattedDate = this.getFormattedDate(start, end);
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
    getRecordClass(record) {
        const { colorIndex } = record;
        const color = getColor(colorIndex);
        if (color && typeof color === "number") {
            return `o_calendar_color_${color}`;
        }
        return "";
    }
    getRecordStyle(record) {
        const { colorIndex } = record;
        const color = getColor(colorIndex);
        if (color && typeof color === "string") {
            return `background-color: ${color};`;
        }
        return "";
    }
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
    getFormattedDate(start, end) {
        const isSameDay = start.hasSame(end, "days");
        if (!isSameDay && start.hasSame(end, "month")) {
            // Simplify date-range if an event occurs into the same month (eg. "August 4-5, 2019")
            return start.toFormat("LLLL d") + "-" + end.toFormat("d, y");
        } else {
            return isSameDay
                ? start.toFormat("DDD")
                : start.toFormat("DDD") + " - " + end.toFormat("DDD");
        }
    }

    onCreateButtonClick() {
        this.props.createRecord({
            start: this.props.date,
            isAllDay: true,
        });
        this.props.close();
    }
    onRecordClick(record) {
        this.props.editRecord(record);
        this.props.close();
    }
}
CalendarYearPopover.components = { Dialog };
CalendarYearPopover.template = "web.CalendarYearPopover";
CalendarYearPopover.subTemplates = {
    popover: "web.CalendarYearPopover.popover",
    body: "web.CalendarYearPopover.body",
    footer: "web.CalendarYearPopover.footer",
    record: "web.CalendarYearPopover.record",
};
CalendarYearPopover.props = {
    close: Function,
    date: true,
    model: Object,
    records: Array,
    createRecord: Function,
    deleteRecord: Function,
    editRecord: Function,
};
