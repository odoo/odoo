import { getLocalYearAndWeek } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import {
    convertRecordToEvent,
    getColor,
    getFullCalendarTimeZone,
    joinClasses,
} from "@web/views/calendar/utils";
import { useCalendarPopover } from "@web/views/calendar/hooks/calendar_popover_hook";
import { useFullCalendar } from "@web/views/calendar/hooks/full_calendar_hook";
import { makeWeekColumn } from "@web/views/calendar/calendar_common/calendar_common_week_column";
import { CalendarYearPopover } from "@web/views/calendar/calendar_year/calendar_year_popover";
import { TOUCH_SELECTION_THRESHOLD } from "@web/views/utils";

import { Component, signal, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

export const calendarYearRendererProps = {
    model: t.object(),
    initialDate: t.object(),
    createRecord: t.function(),
    editRecord: t.function(),
    deleteRecord: t.function(),
    isDisabled: t.boolean().optional(),
    isWeekendVisible: t.boolean().optional(),
};

export class CalendarYearRenderer extends Component {
    static components = {
        Popover: CalendarYearPopover,
    };
    static template = "web.CalendarYearRenderer";
    props = useProps(calendarYearRendererProps);

    fcRef = signal.ref();

    setup() {
        this.fc = useFullCalendar(
            this.fcRef,
            this.props.isDisabled ? this.disabledOptions : this.interactiveOptions
        );
        this.popover = useCalendarPopover(this.constructor.components.Popover);
        this.uiService = useService("ui");
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
            dateClick: this.handleDateClick.bind(this),
            dayMaxEventRows: this.props.model.eventLimit,
            droppable: true,
            editable: this.props.model.canEdit,
            backgroundEventClass: (info) => joinClasses(this.eventClassNames(info)),
            backgroundEventDidMount: this.onEventDidMount.bind(this),
            eventReceive: this.onEventScheduled.bind(this),
            eventResizableFromStart: true,
            longPressDelay: TOUCH_SELECTION_THRESHOLD,
            select: this.onSelect.bind(this),
            selectMinDistance: 5, // needed to not trigger select when click
            selectMirror: true,
            selectable: this.props.model.canCreate,
            unselectAuto: false,
            backgroundEventContent: "",
            weekends: this.props.isWeekendVisible,
        };
    }

    get options() {
        return {
            dayHeaderAlign: "center",
            dayHeaderFormat: { weekday: "narrow" },
            dayCellClass: (info) => joinClasses(this.getDayCellClassNames(info)),
            initialDate: this.props.initialDate.toISO(),
            initialView: "multiMonthYear",
            direction: localization.direction,
            events: (_, successCb) => successCb(this.mapRecordsToEvents()),
            firstDay: this.props.model.firstDayOfWeek,
            headerToolbar: false,
            height: "100%",
            locale: luxon.Settings.defaultLocale,
            navLinks: false,
            nowIndicator: true,
            showNonCurrentDates: false,
            timeZone: getFullCalendarTimeZone(),
            multiMonthMaxColumns: 12,
            singleMonthMinWidth: 352,
            singleMonthTitleFormat: { month: "long", year: "numeric" },
            viewDidMount: this.viewDidMount.bind(this),
            weekNumberCalculation: (date) => getLocalYearAndWeek(date).week,
            weekNumbers: false,
            // the week column replaces the week numbers rendered in the days
            inlineWeekNumberClass: !this.customOptions.weekNumbersWithinDays && "d-none",
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
        const showWeek = view.calendar.getOption("weekNumbers");
        const weekText = view.calendar.getOption("weekTextShort");
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
        // The event might be fired after a touch pointerup without any jsEvent, or after a touch
        // taken over by another gesture (e.g. the swiper)
        if (!info.jsEvent || info.jsEvent.defaultPrevented || info.jsEvent.type === "touchcancel") {
            return;
        }
        this.onDateClick(info);
    }
    openPopover(target, date, records) {
        this.popover.open(target, this.getPopoverProps(date, records), "o_calendar_popover");
    }
    unselect() {
        this.fc().unselect();
    }

    onDateClick(info) {
        if (this.uiService.isSmall) {
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
    eventClassNames({ event, isStart, isEnd }) {
        const classesToAdd = [];
        classesToAdd.push("o_event");
        if (isStart) {
            classesToAdd.push("o_calendar_event_start");
        }
        if (isEnd) {
            classesToAdd.push("o_calendar_event_end");
        }
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
    onEventDidMount({ el, event }) {
        el.dataset.eventId = event.id;
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
}
