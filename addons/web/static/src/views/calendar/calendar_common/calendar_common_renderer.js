/** @odoo-module **/

import { is24HourFormat } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { renderToString } from "@web/core/utils/render";
import { useDebounced } from "@web/core/utils/timing";
import { getColor } from "../colors";
import { useCalendarPopover, useClickHandler, useFullCalendar } from "../hooks";
import { CalendarCommonPopover } from "./calendar_common_popover";

import { Component, useEffect } from "@odoo/owl";

const SCALE_TO_FC_VIEW = {
    day: "timeGridDay",
    week: "timeGridWeek",
    month: "dayGridMonth",
};
const SCALE_TO_HEADER_FORMAT = {
    day: "DDD",
    week: "EEE d",
    month: "EEEE",
};
const SHORT_SCALE_TO_HEADER_FORMAT = {
    ...SCALE_TO_HEADER_FORMAT,
    day: "D",
    month: "EEE",
};
const HOUR_FORMATS = {
    12: {
        hour: "numeric",
        minute: "2-digit",
        omitZeroMinute: true,
        meridiem: "short",
    },
    24: {
        hour: "numeric",
        minute: "2-digit",
        hour12: false,
    },
};

export class CalendarCommonRenderer extends Component {
    setup() {
        this.fc = useFullCalendar("fullCalendar", this.options);
        this.click = useClickHandler(this.onClick, this.onDblClick);
        this.popover = useCalendarPopover(this.constructor.components.Popover);
        this.onWindowResizeDebounced = useDebounced(this.onWindowResize, 200);

        useEffect(() => {
            this.updateSize();
        });

        useEffect(
            (view) => {
                this.env.config.setDisplayName(`${this.props.displayName} (${view.title})`);
            },
            () => [this.fc.api.view]
        );
    }

    get options() {
        return {
            allDaySlot: this.props.model.hasAllDaySlot,
            allDayText: this.env._t("All day"),
            columnHeaderFormat: this.env.isSmall
                ? SHORT_SCALE_TO_HEADER_FORMAT[this.props.model.scale]
                : SCALE_TO_HEADER_FORMAT[this.props.model.scale],
            dateClick: this.onDateClick,
            dayRender: this.onDayRender,
            defaultDate: this.props.model.date.toISO(),
            defaultView: SCALE_TO_FC_VIEW[this.props.model.scale],
            dir: localization.direction,
            droppable: true,
            editable: this.props.model.canEdit,
            eventClick: this.onEventClick,
            eventDragStart: this.onEventDragStart,
            eventDrop: this.onEventDrop,
            eventLimit: this.props.model.eventLimit,
            eventLimitClick: this.onEventLimitClick,
            eventMouseEnter: this.onEventMouseEnter,
            eventMouseLeave: this.onEventMouseLeave,
            eventRender: this.onEventRender,
            eventResizableFromStart: true,
            eventResize: this.onEventResize,
            eventResizeStart: this.onEventResizeStart,
            events: (_, successCb) => successCb(this.mapRecordsToEvents()),
            firstDay: this.props.model.firstDayOfWeek % 7,
            header: false,
            height: "parent",
            locale: luxon.Settings.defaultLocale,
            longPressDelay: 500,
            navLinks: false,
            nowIndicator: true,
            plugins: ["dayGrid", "interaction", "timeGrid", "luxon"],
            select: this.onSelect,
            selectAllow: this.isSelectionAllowed,
            selectMinDistance: 5, // needed to not trigger select when click
            selectMirror: true,
            selectable: this.props.model.canCreate,
            slotLabelFormat: is24HourFormat() ? HOUR_FORMATS[24] : HOUR_FORMATS[12],
            snapDuration: { minutes: 15 },
            timeZone: luxon.Settings.defaultZone.name,
            unselectAuto: false,
            weekLabel:
                this.props.model.scale === "month" && this.env.isSmall ? "" : this.env._t("Week"),
            weekNumberCalculation: "ISO",
            weekNumbers: true,
            weekNumbersWithinDays: !this.env.isSmall,
            windowResize: this.onWindowResizeDebounced,
        };
    }

    getStartTime(record) {
        const timeFormat = is24HourFormat() ? "HH:mm" : "hh:mm a";
        return record.start.toFormat(timeFormat);
    }

    getEndTime(record) {
        const timeFormat = is24HourFormat() ? "HH:mm" : "hh:mm a";
        return record.end.toFormat(timeFormat);
    }

    computeEventSelector(event) {
        return `[data-event-id="${event.id}"]`;
    }
    highlightEvent(event, className) {
        for (const el of this.fc.el.querySelectorAll(this.computeEventSelector(event))) {
            el.classList.add(className);
        }
    }
    unhighlightEvent(event, className) {
        for (const el of this.fc.el.querySelectorAll(this.computeEventSelector(event))) {
            el.classList.remove(className);
        }
    }
    mapRecordsToEvents() {
        return Object.values(this.props.model.records).map((r) => this.convertRecordToEvent(r));
    }
    convertRecordToEvent(record) {
        const allDay = record.isAllDay || record.end.diff(record.start, "hours").hours >= 24;
        return {
            id: record.id,
            title: record.title,
            start: record.start.toISO(),
            end:
                ["week", "month"].includes(this.props.model.scale) &&
                (record.isAllDay ||
                    (allDay && record.end.toMillis() !== record.end.startOf("day").toMillis()))
                    ? record.end.plus({ days: 1 }).toISO()
                    : record.end.toISO(),
            allDay: allDay,
        };
    }
    getPopoverProps(record) {
        return {
            record,
            model: this.props.model,
            createRecord: this.props.createRecord,
            deleteRecord: this.props.deleteRecord,
            editRecord: this.props.editRecord,
        };
    }
    openPopover(target, record) {
        this.popover.open(
            target,
            this.getPopoverProps(record),
            `o_cw_popover o_calendar_color_${record.colorIndex}`
        );
    }
    updateSize() {
        const height = window.innerHeight - this.fc.el.getBoundingClientRect().top;
        this.fc.el.style.height = `${height}px`;
        this.fc.api.updateSize();
    }

    onClick(info) {
        this.openPopover(info.el, this.props.model.records[info.event.id]);
        this.highlightEvent(info.event, "o_cw_custom_highlight");
    }
    onDateClick(info) {
        if (this.env.isSmall && this.props.model.scale === "month") {
            this.props.model.load({
                date: luxon.DateTime.fromISO(info.dateStr),
                scale: "day",
            });
            return;
        }
        this.props.createRecord(this.fcEventToRecord(info));
    }
    onDayRender(info) {
        const date = luxon.DateTime.fromJSDate(info.date).toISODate();
        if (this.props.model.unusualDays.includes(date)) {
            info.el.classList.add("o_calendar_disabled");
        }
    }
    onDblClick(info) {
        this.props.editRecord(this.props.model.records[info.event.id]);
    }
    onEventClick(info) {
        this.click(info);
    }
    onEventRender(info) {
        const { el, event } = info;
        el.dataset.eventId = event.id;
        el.classList.add("o_event", "py-0");
        const record = this.props.model.records[event.id];

        if (record) {
            // This is needed in order to give the possibility to change the event template.
            const injectedContentStr = renderToString(this.constructor.eventTemplate, {
                ...record,
                startTime: this.getStartTime(record),
                endTime: this.getEndTime(record),
            });
            const domParser = new DOMParser();
            const { children } = domParser.parseFromString(injectedContentStr, "text/html").body;
            el.querySelector(".fc-content").replaceWith(...children);

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
            if (record.duration <= 0.25) {
                el.classList.add("o_event_oneliner");
            }
        }

        if (!el.querySelector(".fc-bg")) {
            const bg = document.createElement("div");
            bg.classList.add("fc-bg");
            el.appendChild(bg);
        }
    }
    async onSelect(info) {
        this.popover.close();
        await this.props.createRecord(this.fcEventToRecord(info));
        this.fc.api.unselect();
    }
    isSelectionAllowed(event) {
        return event.end.getDate() === event.start.getDate() || event.allDay;
    }
    onEventDrop(info) {
        this.fc.api.unselect();
        this.props.model.updateRecord(this.fcEventToRecord(info.event), { moved: true });
    }
    onEventResize(info) {
        this.fc.api.unselect();
        this.props.model.updateRecord(this.fcEventToRecord(info.event));
    }
    fcEventToRecord(event) {
        const { id, allDay, date, start, end } = event;
        const res = {
            start: luxon.DateTime.fromJSDate(date || start),
            isAllDay: allDay,
        };
        if (end) {
            res.end = luxon.DateTime.fromJSDate(end);
            if (["week", "month"].includes(this.props.model.scale) && allDay) {
                res.end = res.end.minus({ days: 1 });
            }
        }
        if (id) {
            res.id = this.props.model.records[id].id;
        }
        return res;
    }
    onEventMouseEnter(info) {
        this.highlightEvent(info.event, "o_cw_custom_highlight");
    }
    onEventMouseLeave(info) {
        if (!info.event.id) {
            return;
        }
        this.unhighlightEvent(info.event, "o_cw_custom_highlight");
    }
    onEventDragStart(info) {
        info.el.classList.add(info.view.type);
        this.fc.api.unselect();
        this.highlightEvent(info.event, "o_cw_custom_highlight");
    }
    onEventResizeStart(info) {
        this.fc.api.unselect();
        this.highlightEvent(info.event, "o_cw_custom_highlight");
    }
    onEventLimitClick() {
        this.fc.api.unselect();
        return "popover";
    }
    onWindowResize() {
        this.updateSize();
    }
}
CalendarCommonRenderer.components = {
    Popover: CalendarCommonPopover,
};
CalendarCommonRenderer.template = "web.CalendarCommonRenderer";
CalendarCommonRenderer.eventTemplate = "web.CalendarCommonRenderer.event";
