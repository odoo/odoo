/** @odoo-module **/

import { is24HourFormat } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { renderToString } from "@web/core/utils/render";
import { useDebounced } from "@web/core/utils/timing";
import { getColor } from "../colors";
import { useCalendarPopover, useClickHandler, useFullCalendar } from "../hooks";
import { CalendarCommonPopover } from "./calendar_common_popover";

const { Component, useEffect } = owl;

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
            columnHeaderFormat: SCALE_TO_HEADER_FORMAT[this.props.model.scale],
            dayNames: luxon.Info.weekdays("long"),
            dayNamesShort: luxon.Info.weekdays("short"),
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
            monthNames: luxon.Info.months("long"),
            monthNamesShort: luxon.Info.months("short"),
            navLinks: false,
            nowIndicator: true,
            plugins: ["dayGrid", "interaction", "timeGrid", "luxon"],
            select: this.onSelect,
            selectAllow: this.isSelectionAllowed,
            selectMirror: true,
            selectable: this.props.model.canCreate,
            slotLabelFormat: is24HourFormat() ? HOUR_FORMATS[24] : HOUR_FORMATS[12],
            snapDuration: { minutes: 15 },
            timeZone: luxon.Settings.defaultZone.name,
            unselectAuto: false,
            weekLabel: this.env._t("Week"),
            weekNumberCalculation: "ISO",
            weekNumbers: true,
            weekNumbersWithinDays: true,
            windowResize: this.onWindowResizeDebounced,
        };
    }

    getStartTime(record) {
        const timeFormat = is24HourFormat() ? "HH:mm" : "hh:mm a";
        return record.start.toFormat(timeFormat);
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
        return {
            id: record.id,
            title: record.title,
            start: record.start.toISO(),
            end:
                ["week", "month"].includes(this.props.model.scale) && record.isAllDay
                    ? record.end.plus({ days: 1 }).toISO()
                    : record.end.toISO(),
            allDay: record.isAllDay,
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
            const injectedContentStr = renderToString(this.constructor.eventTemplate, {
                ...record,
                startTime: this.getStartTime(record),
            });
            const domParser = new DOMParser();
            const injectedContent = domParser.parseFromString(injectedContentStr, "application/xml")
                .documentElement;
            el.replaceChild(injectedContent, el.querySelector(".fc-content"));

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

        if (!el.querySelector(".fc-bg")) {
            const bg = document.createElement("div");
            bg.classList.add("fc-bg");
            el.appendChild(bg);
        }
    }
    async onSelect(info) {
        this.popover.close();
        await this.props.createRecord(this.FCEventToRecord(info));
        this.fc.api.unselect();
    }
    isSelectionAllowed(event) {
        return event.end.getDate() === event.start.getDate() || event.allDay;
    }
    onEventDrop(info) {
        this.fc.api.unselect();
        this.props.model.updateRecord(this.FCEventToRecord(info.event), { moved: true });
    }
    onEventResize(info) {
        this.fc.api.unselect();
        this.props.model.updateRecord(this.FCEventToRecord(info.event));
    }
    FCEventToRecord(event) {
        const { id, allDay, start, end } = event;
        let luxonEnd = luxon.DateTime.fromJSDate(end);
        if (["week", "month"].includes(this.props.model.scale) && allDay) {
            luxonEnd = luxonEnd.minus({ days: 1 });
        }

        const res = {
            start: luxon.DateTime.fromJSDate(start),
            end: luxonEnd,
            isAllDay: allDay,
        };
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
