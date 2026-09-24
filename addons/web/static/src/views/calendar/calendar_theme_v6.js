import { joinClasses } from "@web/views/calendar/utils";

const DOW_NAMES = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

function dateClasses(info) {
    return [
        "fc-day",
        `fc-day-${DOW_NAMES[info.dow]}`,
        info.isToday && "fc-day-today",
        info.isPast && "fc-day-past",
        info.isFuture && "fc-day-future",
        info.isOther && "fc-day-other",
        info.isDisabled && "fc-day-disabled",
    ];
}

function eventRangeClasses(info) {
    return [
        info.isStart && "fc-event-start",
        info.isEnd && "fc-event-end",
        info.isPast && "fc-event-past",
        info.isFuture && "fc-event-future",
        info.isToday && "fc-event-today",
    ];
}

function eventClasses(info) {
    return joinClasses(
        "fc-event",
        ...eventRangeClasses(info),
        info.isMirror && "fc-event-mirror",
        info.isDragging && "fc-event-dragging",
        info.isResizing && "fc-event-resizing",
        info.isSelected && "fc-event-selected",
        info.isDraggable && "fc-event-draggable",
        (info.isStartResizable || info.isEndResizable) && "fc-event-resizable"
    );
}

/**
 * FullCalendar v7 no longer exposes stable class names (its own classes are hashed) nor ships a
 * default theme. This theme restores the v6 semantic class names we style and query. As a plugin,
 * its class options are joined with the ones given by the renderers.
 */
export const v6CalendarTheme = {
    name: "theme-v6",
    optionDefaults: {
        className: "fc",
        viewClass: (info) => joinClasses("fc-view", `fc-${info.view.type}-view`),
        dayHeaderClass: (info) => joinClasses(dateClasses(info), "fc-col-header-cell"),
        dayHeaderInnerClass: "fc-col-header-cell-cushion",
        dayHeaderRowClass: "fc-col-header-row",
        dayCellClass: (info) => joinClasses(dateClasses(info), "fc-daygrid-day"),
        dayCellTopClass: "fc-daygrid-day-top",
        dayCellTopInnerClass: "fc-daygrid-day-number",
        dayCellInnerClass: "fc-daygrid-day-events",
        dayCellBottomClass: "fc-daygrid-day-bottom",
        dayLaneClass: (info) => joinClasses(dateClasses(info), "fc-timegrid-col"),
        dayLaneInnerClass: "fc-timegrid-col-events",
        slotLaneClass: (info) =>
            joinClasses(
                "fc-timegrid-slot",
                "fc-timegrid-slot-lane",
                info.isMinor && "fc-timegrid-slot-minor"
            ),
        slotHeaderClass: (info) =>
            joinClasses(
                "fc-timegrid-slot",
                "fc-timegrid-slot-label",
                info.isMinor && "fc-timegrid-slot-minor"
            ),
        slotHeaderInnerClass: "fc-timegrid-slot-label-cushion",
        allDayHeaderClass: "fc-timegrid-axis",
        allDayHeaderInnerClass: "fc-timegrid-axis-cushion",
        weekNumberHeaderClass: "fc-timegrid-axis fc-week-number",
        weekNumberHeaderInnerClass: "fc-timegrid-axis-cushion",
        allDayDividerClass: "fc-timegrid-divider",
        inlineWeekNumberClass: "fc-daygrid-week-number",
        eventClass: eventClasses,
        eventInnerClass: "fc-event-main",
        eventTimeClass: "fc-event-time",
        eventTitleClass: "fc-event-title",
        rowEventClass: "fc-daygrid-event fc-daygrid-block-event",
        columnEventClass: "fc-timegrid-event",
        listItemEventClass: "fc-daygrid-event fc-daygrid-dot-event",
        listItemEventBeforeClass: "fc-daygrid-event-dot",
        rowEventBeforeClass: (info) =>
            info.isStartResizable && "fc-event-resizer fc-event-resizer-start",
        rowEventAfterClass: (info) =>
            info.isEndResizable && "fc-event-resizer fc-event-resizer-end",
        columnEventBeforeClass: (info) =>
            info.isStartResizable && "fc-event-resizer fc-event-resizer-start",
        columnEventAfterClass: (info) =>
            info.isEndResizable && "fc-event-resizer fc-event-resizer-end",
        backgroundEventClass: (info) => joinClasses("fc-bg-event", eventRangeClasses(info)),
        moreLinkClass: "fc-more-link",
        rowMoreLinkClass: "fc-daygrid-more-link",
        columnMoreLinkClass: "fc-timegrid-more-link",
        nowIndicatorHeaderClass: "fc-timegrid-now-indicator-arrow",
        nowIndicatorLineClass: "fc-timegrid-now-indicator-line",
        toolbarClass: "fc-toolbar fc-header-toolbar",
        toolbarSectionClass: "fc-toolbar-chunk",
        toolbarTitleClass: "fc-toolbar-title",
        // rendered in the body, its events must look like the calendar ones
        popoverClass: "fc-popover fc-more-popover o_calendar_renderer",
        popoverCloseClass: "fc-popover-close",
        highlightClass: "fc-highlight",
        nonBusinessHoursClass: "fc-non-business",
        tableHeaderClass: "fc-scrollgrid-section-header",
        tableBodyClass: "fc-scrollgrid-section-body",
        dayRowClass: "fc-daygrid-row",
    },
};
