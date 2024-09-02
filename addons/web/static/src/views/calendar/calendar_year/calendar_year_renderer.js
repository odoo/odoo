import { localization } from "@web/core/l10n/localization";
import { useDebounced } from "@web/core/utils/timing";
import { getColor } from "../colors";
import { useCalendarPopover, useFullCalendar } from "../hooks";
import { CalendarYearPopover } from "./calendar_year_popover";
import { makeWeekColumn } from "@web/views/calendar/calendar_common/calendar_common_week_column";
import { getLocalWeekNumber } from "@web/core/l10n/dates";

import { Component, useEffect, useRef } from "@odoo/owl";

export class CalendarYearRenderer extends Component {
    static components = {
        Popover: CalendarYearPopover,
    };
    static template = "web.CalendarYearRenderer";
    static props = {
        model: Object,
        displayName: { type: String, optional: true },
        isWeekendVisible: { type: Boolean, optional: true },
        createRecord: Function,
        editRecord: Function,
        deleteRecord: Function,
        setDate: { type: Function, optional: true },
    };

    setup() {
        this.months = luxon.Info.months();
        this.fcs = {};
        for (const month of this.months) {
            this.fcs[month] = useFullCalendar(
                `fullCalendar-${month}`,
                this.getOptionsForMonth(month)
            );
        }
        this.popover = useCalendarPopover(this.constructor.components.Popover);
        this.rootRef = useRef("root");
        this.onWindowResizeDebounced = useDebounced(this.onWindowResize, 200);

        useEffect(() => {
            this.updateSize();
        });
    }

    get options() {
        return {
            dayHeaderFormat: "EEEEE",
            dateClick: this.onDateClick,
            dayCellClassNames: this.getDayCellClassNames,
            initialDate: this.props.model.date.toISO(),
            initialView: "dayGridMonth",
            direction: localization.direction,
            droppable: true,
            editable: this.props.model.canEdit,
            dayMaxEventRows: this.props.model.eventLimit,
            eventClassNames: this.eventClassNames,
            eventDidMount: this.onEventDidMount,
            eventResizableFromStart: true,
            events: (_, successCb) => successCb(this.mapRecordsToEvents()),
            firstDay: this.props.model.firstDayOfWeek,
            headerToolbar: { start: false, center: "title", end: false },
            height: "auto",
            locale: luxon.Settings.defaultLocale,
            longPressDelay: 500,
            navLinks: false,
            nowIndicator: true,
            select: this.onSelect,
            selectMinDistance: 5, // needed to not trigger select when click
            selectMirror: true,
            selectable: this.props.model.canCreate,
            showNonCurrentDates: false,
            timeZone: luxon.Settings.defaultZone.name,
            titleFormat: { month: "long", year: "numeric" },
            unselectAuto: false,
            weekNumberCalculation: (date) => getLocalWeekNumber(date),
            weekNumbers: false,
            weekNumberFormat: { week: "numeric" },
            windowResize: this.onWindowResizeDebounced,
            eventContent: this.onEventContent,
            viewDidMount: this.viewDidMount,
            weekends: this.props.isWeekendVisible,
        };
    }

    get customOptions() {
        return {
            weekNumbersWithinDays: true,
        };
    }

    viewDidMount({ el, view }) {
        const showWeek = view.calendar.currentData.options.weekNumbers;
        const weekText = view.calendar.currentData.options.weekText;
        const weekColumn = !this.customOptions.weekNumbersWithinDays;
        if (showWeek && weekColumn) {
            makeWeekColumn({ el, weekText });
        }
    }

    mapRecordsToEvents() {
        return Object.values(this.props.model.records).map((r) => this.convertRecordToEvent(r));
    }
    convertRecordToEvent(record) {
        return {
            id: record.id,
            title: record.title,
            start: record.start.toISO(),
            end: record.end.plus({ day: 1 }).toISO(),
            allDay: true,
            display: "background",
        };
    }
    getDateWithMonth(month) {
        return this.props.model.date.set({ month: this.months.indexOf(month) + 1 }).toISO();
    }
    getOptionsForMonth(month) {
        return {
            ...this.options,
            initialDate: this.getDateWithMonth(month),
        };
    }
    getPopoverProps(date, records) {
        return {
            date,
            records,
            model: this.props.model,
            createRecord: this.props.createRecord,
            deleteRecord: this.props.deleteRecord,
            editRecord: this.props.editRecord,
        };
    }
    openPopover(target, date, records) {
        this.popover.open(target, this.getPopoverProps(date, records), "o_cw_popover");
    }
    unselect() {
        for (const fc of Object.values(this.fcs)) {
            fc.api.unselect();
        }
    }
    updateSize() {
        const height = window.innerHeight - this.rootRef.el.getBoundingClientRect().top;
        this.rootRef.el.style.height = `${height}px`;
    }

    onDateClick(info) {
        if (this.env.isSmall) {
            this.props.model.load({
                date: luxon.DateTime.fromISO(info.dateStr),
                scale: "day",
            });
            return;
        }

        // With date value we don't want to change the time, we need the exact date
        const date = luxon.DateTime.fromISO(info.dateStr);
        const records = Object.values(this.props.model.records).filter((r) =>
            luxon.Interval.fromDateTimes(r.start.startOf("day"), r.end.endOf("day")).contains(date)
        );

        this.popover.close();
        if (records.length) {
            const target = info.dayEl;
            this.openPopover(target, date, records);
        } else if (this.props.model.canCreate) {
            this.props.createRecord({
                // With date value we don't want to change the time, we need the exact date
                start: luxon.DateTime.fromISO(info.dateStr),
                isAllDay: true,
            });
        }
    }
    getDayCellClassNames(info) {
        const date = luxon.DateTime.fromJSDate(info.date).toISODate();
        if (this.props.model.unusualDays.includes(date)) {
            return ["o_calendar_disabled"];
        }
        return [];
    }
    eventClassNames({ event }) {
        const classesToAdd = [];
        classesToAdd.push("o_event");
        const record = this.props.model.records[event.id];
        if (record) {
            const color = getColor(record.colorIndex);
            if (typeof color === "number") {
                classesToAdd.push(`o_calendar_color_${color}`);
            } else if (typeof color !== "string") {
                classesToAdd.push("o_calendar_color_0");
            }

            if (record.isHatched) {
                classesToAdd.push("o_event_hatched");
            }
            if (record.isStriked) {
                classesToAdd.push("o_event_striked");
            }
        }
        return classesToAdd;
    }
    onEventDidMount(info) {
        const { el, event } = info;
        el.dataset.eventId = event.id;
        const record = this.props.model.records[event.id];
        if (record) {
            const color = getColor(record.colorIndex);
            if (typeof color === "string") {
                el.style.backgroundColor = color;
            }
        }
    }
    async onSelect(info) {
        this.popover.close();
        await this.props.createRecord({
            // With date value we don't want to change the time, we need the exact date
            start: luxon.DateTime.fromISO(info.startStr),
            end: luxon.DateTime.fromISO(info.endStr).minus({ days: 1 }),
            isAllDay: true,
        });
        this.unselect();
    }
    onWindowResize() {
        this.updateSize();
    }

    onEventContent(info) {
        // Remove the title on the background event like in FCv4
        if (info.event.display?.includes("background")) {
            return null;
        }
    }
}
