/** @odoo-module **/

import { formatDate } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { useDebounced } from "@web/core/utils/timing";
import { getColor } from "../colors";
import { calculateWeekNumber } from "../date_utils";
import { useCalendarPopover, useFullCalendar } from "../hooks";
import { CalendarYearPopover } from "./calendar_year_popover";

const { Component, useEffect, useRef, onRendered } = owl;

export class CalendarYearRenderer extends Component {
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

        onRendered(() => {
            const year = formatDate(this.props.model.date, { format: "yyyy" });
            this.env.config.setDisplayName(`${this.props.displayName} (${year})`);
        });
    }

    get options() {
        return {
            columnHeaderFormat: (info) =>
                luxon.DateTime.fromJSDate(info.date.marker).toFormat("EEEEE"),
            contentHeight: 0,
            dateClick: this.onDateClick,
            dayNames: luxon.Info.weekdays("long"),
            dayNamesShort: luxon.Info.weekdays("short"),
            dayRender: this.onDayRender,
            defaultDate: this.props.model.date.toJSDate(),
            defaultView: "dayGridMonth",
            dir: localization.direction,
            droppable: true,
            editable: this.props.model.canEdit,
            eventLimit: this.props.model.eventLimit,
            eventRender: this.onEventRender,
            eventResizableFromStart: true,
            events: (_, successCb) => successCb(this.mapRecordsToEvents()),
            firstDay: this.props.model.firstDayOfWeek,
            header: { left: false, center: "title", right: false },
            height: 0,
            locale: "en-US",
            longPressDelay: 500,
            monthNames: luxon.Info.months("long"),
            monthNamesShort: luxon.Info.months("short"),
            navLinks: false,
            nowIndicator: true,
            plugins: ["dayGrid", "interaction"],
            select: this.onSelect,
            selectMinDistance: 5, // needed to not trigger select when click
            selectMirror: true,
            selectable: this.props.model.canCreate,
            showNonCurrentDates: false,
            titleFormat: { month: "short", year: "numeric" },
            unselectAuto: false,
            weekNumberCalculation: calculateWeekNumber,
            weekNumbers: false,
            windowResize: this.onWindowResizeDebounced,
        };
    }

    mapRecordsToEvents() {
        return Object.values(this.props.model.records).map((r) => this.convertRecordToEvent(r));
    }
    convertRecordToEvent(record) {
        return {
            id: record.id,
            title: record.title,
            start: record.start.startOf("day").toJSDate(),
            end: record.end.startOf("day").plus({ days: 1 }).toJSDate(),
            allDay: true,
            rendering: "background",
        };
    }
    getDateWithMonth(month) {
        return this.props.model.date.set({ month: this.months.indexOf(month) + 1 }).toJSDate();
    }
    getOptionsForMonth(month) {
        return {
            ...this.options,
            defaultDate: this.getDateWithMonth(month),
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
        this.popover.open(target, this.getPopoverProps(date, records));
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
        // With date value we don't want to change the time, we need the exact date
        const date = luxon.DateTime.fromJSDate(info.date);
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
                start: luxon.DateTime.fromJSDate(info.date),
                isAllDay: true,
            });
        }
    }
    onDayRender(info) {
        const date = luxon.DateTime.fromJSDate(info.date).toISODate();
        if (this.props.model.unusualDays.includes(date)) {
            info.el.classList.add("o_calendar_disabled");
        }
    }
    onEventRender(info) {
        const { el, event } = info;
        el.dataset.eventId = event.id;
        el.classList.add("o_event");
        const record = this.props.model.records[event.id];
        if (record) {
            const color = getColor(record.colorIndex);
            if (typeof color === "string") {
                el.style.backgroundColor = color;
            } else if (typeof color === "number") {
                el.classList.add(`o_calendar_color_${color}`);
            } else {
                el.classList.add("o_calendar_color_1");
            }

            if (record.isHatched) {
                el.classList.add("o_event_hatched");
            }
            if (record.isStriked) {
                el.classList.add("o_event_striked");
            }
        }
    }
    async onSelect(info) {
        this.popover.close();
        await this.props.createRecord({
            // With date value we don't want to change the time, we need the exact date
            start: luxon.DateTime.fromJSDate(info.start),
            end: luxon.DateTime.fromJSDate(info.end),
            isAllDay: true,
        });
        this.unselect();
    }
    onWindowResize() {
        this.updateSize();
    }
}
CalendarYearRenderer.components = {
    Popover: CalendarYearPopover,
};
CalendarYearRenderer.template = "web.CalendarYearRenderer";
