import { getLocalYearAndWeek } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { convertRecordToEvent, getColor } from "@web/views/calendar/utils";
import { useCalendarPopover } from "@web/views/calendar/hooks/calendar_popover_hook";
import { useFullCalendar } from "@web/views/calendar/hooks/full_calendar_hook";
import { makeWeekColumn } from "@web/views/calendar/calendar_common/calendar_common_week_column";
import { CalendarYearPopover } from "@web/views/calendar/calendar_year/calendar_year_popover";
import { TOUCH_SELECTION_THRESHOLD } from "@web/views/utils";

import { Component, useEffect, useRef } from "@odoo/owl";

const { DateTime } = luxon;

export class CalendarYearRenderer extends Component {
    static components = {
        Popover: CalendarYearPopover,
    };
    static template = "web.CalendarYearRenderer";
    static props = {
        model: Object,
        initialDate: Object,
        createRecord: Function,
        editRecord: Function,
        deleteRecord: Function,
        isDisabled: { type: Boolean, optional: true },
        isWeekendVisible: { type: Boolean, optional: true },
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

        useEffect(() => {
            this.updateSize();
        });
    }

    get disabledOptions() {
        return {
            ...this.options,
            editable: false,
            selectable: false,
            eventStartEditable: false,
            eventDurationEditable: false,
            droppable: false,
        };
    }

    get interactiveOptions() {
        return {
            ...this.options,
            dateClick: this.handleDateClick,
            dayMaxEventRows: this.props.model.eventLimit,
            droppable: true,
            editable: this.props.model.canEdit,
            eventClassNames: this.eventClassNames,
            eventDidMount: this.onEventDidMount,
            eventReceive: this.onEventScheduled,
            eventResizableFromStart: true,
            longPressDelay: TOUCH_SELECTION_THRESHOLD,
            select: this.onSelect,
            selectMinDistance: 5, // needed to not trigger select when click
            selectMirror: true,
            selectable: this.props.model.canCreate,
            unselectAuto: false,
            windowResize: this.onWindowResize,
            eventContent: this.onEventContent,
            weekends: this.props.isWeekendVisible,
        };
    }

    get options() {
        return {
            dayHeaderFormat: "EEEEE",
            dayCellClassNames: this.getDayCellClassNames,
            initialDate: this.props.initialDate.toISO(),
            initialView: "dayGridMonth",
            direction: localization.direction,
            events: (_, successCb) => successCb(this.mapRecordsToEvents()),
            firstDay: this.props.model.firstDayOfWeek,
            headerToolbar: { start: false, center: "title", end: false },
            height: "auto",
            locale: luxon.Settings.defaultLocale,
            navLinks: false,
            nowIndicator: true,
            showNonCurrentDates: false,
            timeZone: luxon.Settings.defaultZone.name,
            titleFormat: { month: "long", year: "numeric" },
            viewDidMount: this.viewDidMount,
            weekNumberCalculation: (date) => getLocalYearAndWeek(date).week,
            weekNumbers: false,
            weekNumberFormat: { week: "numeric" },
            fixedWeekCount: false,
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
        const { records } = this.props.model.data;
        return Object.values(records).map((r) => this.convertRecordToEvent(r));
    }
    convertRecordToEvent(record) {
        return {
            ...convertRecordToEvent(record, true),
            display: "background",
        };
    }
    getDateWithMonth(month) {
        return this.props.initialDate.set({ month: this.months.indexOf(month) + 1 }).toISO();
    }
    getOptionsForMonth(month) {
        const options = this.props.isDisabled ? this.disabledOptions : this.interactiveOptions;
        return {
            ...options,
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
    handleDateClick(info) {
        if (!info.jsEvent || info.jsEvent.defaultPrevented) {
            // The event might be fired after a touch pointerup without any jsEvent
            return;
        }
        this.onDateClick(info);
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
    async onEventScheduled(info) {
        const original = info.event;
        const date = DateTime.fromJSDate(original.start);
        const resId = Number(original.id);
        await this.props.model.scheduleEvent(resId, date);
        original.remove();
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
