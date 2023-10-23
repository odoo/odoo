/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { useDebounced } from "@web/core/utils/timing";
import { getColor } from "../colors";
import { useCalendarPopover, useFullCalendar } from "../hooks";
import { CalendarYearPopover } from "./calendar_year_popover";

import { Component, useEffect, useRef } from "@odoo/owl";

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
    }

    get options() {
        return {
            columnHeaderFormat: "EEEEE",
            contentHeight: 0,
            dateClick: this.onDateClick,
            dayRender: this.onDayRender,
            defaultDate: this.props.model.date.toISO(),
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
            locale: luxon.Settings.defaultLocale,
            longPressDelay: 500,
            navLinks: false,
            nowIndicator: true,
            plugins: ["dayGrid", "interaction", "luxon"],
            select: this.onSelect,
            selectMinDistance: 5, // needed to not trigger select when click
            selectMirror: true,
            selectable: this.props.model.canCreate,
            showNonCurrentDates: false,
            timeZone: luxon.Settings.defaultZone.name,
            titleFormat: { month: "long", year: "numeric" },
            unselectAuto: false,
            weekNumberCalculation: "ISO",
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
            start: record.start.toISO(),
            end: record.end.plus({ day: 1 }).toISO(),
            allDay: true,
            rendering: "background",
        };
    }
    getDateWithMonth(month) {
        return this.props.model.date.set({ month: this.months.indexOf(month) + 1 }).toISO();
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
                el.classList.add("o_calendar_color_0");
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
            start: luxon.DateTime.fromISO(info.startStr),
            end: luxon.DateTime.fromISO(info.endStr).minus({ days: 1 }),
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
