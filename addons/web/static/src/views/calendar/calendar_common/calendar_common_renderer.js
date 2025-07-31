import { browser } from "@web/core/browser/browser";
import { getLocalYearAndWeek } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { is24HourFormat } from "@web/core/l10n/time";
import { useBus } from "@web/core/utils/hooks";
import { renderToFragment, renderToString } from "@web/core/utils/render";
import { useDebounced } from "@web/core/utils/timing";
import { makeWeekColumn } from "@web/views/calendar/calendar_common/calendar_common_week_column";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { convertRecordToEvent, getColor } from "@web/views/calendar/utils";
import { useCalendarPopover } from "@web/views/calendar/hooks/calendar_popover_hook";
import { useFullCalendar } from "@web/views/calendar/hooks/full_calendar_hook";
import { useSquareSelection } from "@web/views/calendar/hooks/square_selection_hook";

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

const { DateTime } = luxon;

export class CalendarCommonRenderer extends Component {
    static components = {
        Popover: CalendarCommonPopover,
    };
    static template = "web.CalendarCommonRenderer";
    static eventTemplate = "web.CalendarCommonRenderer.event";
    static headerTemplate = "web.CalendarCommonRendererHeader";
    static props = {
        model: Object,
        isWeekendVisible: { type: Boolean, optional: true },
        createRecord: Function,
        editRecord: Function,
        deleteRecord: Function,
        setDate: { type: Function, optional: true },
        callbackRecorder: Object,
        onSquareSelection: Function,
        cleanSquareSelection: Function,
    };

    setup() {
        this.fc = useFullCalendar("fullCalendar", this.options);
        this.clickTimeoutId = null;
        this.popover = useCalendarPopover(this.constructor.components.Popover);

        useBus(this.props.model.bus, "SCROLL_TO_CURRENT_HOUR", () =>
            this.fc.api.scrollToTime(`${luxon.DateTime.local().hour - 2}:00:00`)
        );

        const fullCalendarRenderDebounced = useDebounced(() => this.fc.api.updateSize(), 100, {
            immediate: true,
            trailing: true,
        });
        const fullCalendarResizeObserver = new ResizeObserver(fullCalendarRenderDebounced);
        useEffect(
            (el) => {
                fullCalendarResizeObserver.observe(el);
                return () => fullCalendarResizeObserver.unobserve(el);
            },
            () => [this.fc.el]
        );
        useSquareSelection();
    }

    get options() {
        return {
            allDaySlot: true,
            allDayContent: "",
            dayHeaderFormat: this.env.isSmall
                ? SHORT_SCALE_TO_HEADER_FORMAT[this.props.model.scale]
                : SCALE_TO_HEADER_FORMAT[this.props.model.scale],
            // we must handle clicks differently in multicreate mode:
            // fc is blocked by safePrevent in onPointerDown (draggable_hook_builder.js)
            dateClick: this.props.model.hasMultiCreate ? () => {} : this.onDateClick,
            dayCellClassNames: this.getDayCellClassNames,
            initialDate: this.props.model.date.toISO(),
            initialView: SCALE_TO_FC_VIEW[this.props.model.scale],
            direction: localization.direction,
            droppable: true,
            editable: this.props.model.canEdit,
            eventClick: this.onEventClick,
            eventDragStart: this.onEventDragStart,
            eventDrop: this.onEventDrop,
            dayMaxEventRows: this.props.model.eventLimit,
            moreLinkClick: this.onEventLimitClick,
            eventMouseEnter: this.onEventMouseEnter,
            eventMouseLeave: this.onEventMouseLeave,
            eventClassNames: this.eventClassNames,
            eventDidMount: this.onEventDidMount,
            eventContent: this.onEventContent,
            eventResizableFromStart: true,
            eventResize: this.onEventResize,
            eventResizeStart: this.onEventResizeStart,
            events: (_, successCb) => successCb(this.mapRecordsToEvents()),
            firstDay: this.props.model.firstDayOfWeek,
            headerToolbar: false,
            height: "100%",
            locale: luxon.Settings.defaultLocale,
            longPressDelay: 500,
            navLinks: false,
            nowIndicator: true,
            nowIndicatorContent: {
                html: `
                    <div class="o_calendar_time_indicator_now"></div>
                `,
            },
            select: this.onSelect,
            selectAllow: this.isSelectionAllowed,
            selectMinDistance: 5, // needed to not trigger select when click
            selectMirror: true,
            selectable: !this.props.model.hasMultiCreate && this.props.model.canCreate,
            showNonCurrentDates: this.props.model.monthOverflow,
            slotLabelFormat: is24HourFormat() ? HOUR_FORMATS[24] : HOUR_FORMATS[12],
            snapDuration: { minutes: 15 },
            timeZone: luxon.Settings.defaultZone.name,
            unselectAuto: false,
            weekNumberFormat: {
                week: this.props.model.scale === "month" || this.env.isSmall ? "numeric" : "long",
            },
            weekends: this.props.isWeekendVisible,
            weekNumberCalculation: (date) => getLocalYearAndWeek(date).week,
            weekNumbers: true,
            dayHeaderContent: this.getHeaderHtml,
            eventDisplay: "block", // Restore old render in daygrid view for single-day timed events
            eventTimeFormat: is24HourFormat() ? HOUR_FORMATS[24] : HOUR_FORMATS[12],
            viewDidMount: this.viewDidMount,
            moreLinkDidMount: this.wrapMoreLink,
            fixedWeekCount: false,
        };
    }

    get customOptions() {
        return {
            weekNumbersWithinDays: !this.env.isSmall,
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
        return convertRecordToEvent(record);
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
        const color = getColor(record.colorIndex);
        this.popover.open(
            target,
            this.getPopoverProps(record),
            `o_cw_popover card o_calendar_color_${typeof color === "number" ? color : 0}`
        );
    }

    onClick(info) {
        this.openPopover(info.el, this.props.model.records[info.event.id]);
        this.highlightEvent(info.event, "o_cw_custom_highlight");
    }
    onDateClick(info) {
        if (info.jsEvent.defaultPrevented) {
            return;
        }
        this.props.createRecord(this.fcEventToRecord(info));
    }
    getDayCellClassNames(info) {
        const date = luxon.DateTime.fromJSDate(info.date).toISODate();
        if (this.props.model.unusualDays.includes(date)) {
            return ["o_calendar_disabled"];
        }
        return [];
    }
    onDblClick(info) {
        this.props.editRecord(this.props.model.records[info.event.id]);
    }
    onEventClick(info) {
        if (this.clickTimeoutId) {
            this.onDblClick(info);
            browser.clearTimeout(this.clickTimeoutId);
            this.clickTimeoutId = null;
        } else {
            this.clickTimeoutId = browser.setTimeout(() => {
                this.onClick(info);
                this.clickTimeoutId = null;
            }, 250);
        }
    }
    onEventContent({ event }) {
        const record = this.props.model.records[event.id];
        if (record) {
            // This is needed in order to give the possibility to change the event template.
            const fragment = renderToFragment(this.constructor.eventTemplate, {
                ...record,
                startTime: this.getStartTime(record),
                endTime: this.getEndTime(record),
            });
            return { domNodes: fragment.children };
        }
        return true;
    }
    eventClassNames({ el, event }) {
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
            if (record.duration <= 0.25) {
                classesToAdd.push("o_event_oneliner");
            }
            if (DateTime.now() >= record.end) {
                classesToAdd.push("o_past_event");
            }

            if (!record.isAllDay && !record.isTimeHidden && record.isMonth) {
                classesToAdd.push("o_event_dot");
            } else if (record.isAllDay) {
                classesToAdd.push("o_event_allday");
            }
        }
        return classesToAdd;
    }
    onEventDidMount({ el, event }) {
        el.dataset.eventId = event.id;
        const record = this.props.model.records[event.id];

        if (record) {
            if (record.isMonth) {
                el.querySelector(".fc-event-main").classList.add(
                    "d-flex",
                    "gap-1",
                    "text-truncate"
                );
            }
            const color = getColor(record.colorIndex);
            if (typeof color === "string") {
                el.style.backgroundColor = color;
            }

            if (!el.classList.contains("fc-bg")) {
                const bg = document.createElement("div");
                bg.classList.add("fc-bg");
                el.appendChild(bg);
            }
        }
    }
    async onSelect(info) {
        info.jsEvent.preventDefault();
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
            const existingRecord = this.props.model.records[id];
            if (this.props.model.scale === "month") {
                res.start = res.start?.set({
                    hour: existingRecord.start.hour,
                    minute: existingRecord.start.minute,
                });
                if (existingRecord.end) {
                    res.end = res.end?.set({
                        hour: existingRecord.end.hour,
                        minute: existingRecord.end.minute,
                    });
                }
            }
            res.id = existingRecord.id;
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
        this.props.cleanSquareSelection();
        info.el.classList.add(info.view.type);
        this.fc.api.unselect();
        this.highlightEvent(info.event, "o_cw_custom_highlight");
    }
    onEventResizeStart(info) {
        this.props.cleanSquareSelection();
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

    getHeaderHtml({ date }) {
        return {
            html: renderToString(this.constructor.headerTemplate, this.headerTemplateProps(date)),
        };
    }

    headerTemplateProps(date) {
        const scale = this.props.model.scale;
        // when rendering months, FullCalendar uses a date w/out tz
        // so use UTC instead of local tz when converting to DateTime
        const options = scale === "month" ? { zone: "UTC" } : {};
        const { weekdayShort, weekdayLong, day } = DateTime.fromJSDate(date, options);
        return {
            weekdayShort,
            weekdayLong,
            day,
            scale,
        };
    }

    wrapMoreLink({ el }) {
        const wrapper = document.createElement("div");
        wrapper.classList.add("fc-more-cell");
        el.classList.remove("fc-daygrid-more-link");
        el.parentNode.insertBefore(wrapper, el);
        wrapper.appendChild(el);
    }
}
