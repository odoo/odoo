import { joinClasses } from "@web/views/calendar/utils";

/**
 * Odoo theme of FullCalendar, forked from its Monarch (Material Design) theme.
 *
 * The class names are given through the FullCalendar class options: Bootstrap utilities when
 * possible, and `o_calendar_*` classes styled with the "odoo" palette (`--o-calendar-*` variables
 * of `calendar_theme.css`) otherwise. As a plugin, its class options are joined with the ones
 * given by the renderers.
 */

const resizerClass = "o_calendar_resizer position-absolute";

const borderedGridClasses = {
    dayHeaderRowClass: "border",
    dayHeaderClass: "border",
    dayRowClass: "border",
    dayCellClass: "border",
};

export const odooCalendarTheme = {
    name: "theme-odoo",
    optionDefaults: {
        viewClass: (info) =>
            joinClasses("o_calendar_fc_view bg-view", `o_calendar_fc_view_${info.view.type}`),

        /* Events */

        eventClass: "o_calendar_event position-relative overflow-hidden cursor-pointer smaller",
        eventInnerClass: "o_calendar_event_main",
        rowEventClass: "o_calendar_row_event",
        columnEventClass: "o_calendar_column_event",
        // the resizers are only rendered when they have a class
        rowEventBeforeClass: (info) =>
            info.isStartResizable && `${resizerClass} o_calendar_resizer_start top-0 bottom-0`,
        rowEventAfterClass: (info) =>
            info.isEndResizable && `${resizerClass} o_calendar_resizer_end top-0 bottom-0`,
        columnEventBeforeClass: (info) =>
            info.isStartResizable && `${resizerClass} o_calendar_resizer_start start-0 end-0`,
        columnEventAfterClass: (info) =>
            info.isEndResizable && `${resizerClass} o_calendar_resizer_end start-0 end-0`,
        backgroundEventClass: "o_calendar_fill o_calendar_bg_event",

        /* More-link and its popover */

        moreLinkClass: "o_calendar_more_link align-self-center cursor-pointer",
        // rendered in the body, its events must look like the calendar ones
        popoverClass: "o_calendar_more_popover o_calendar_renderer border shadow-sm bg-view",
        popoverCloseClass:
            "o_calendar_more_popover_close position-absolute top-0 end-0 m-1 p-1 border-0 bg-transparent",
        popoverCloseContent: {
            html: `<i class="oi" data-icon="close_small" aria-hidden="true"></i>`,
        },

        /* Day header */

        dayHeaderRowClass: "o_calendar_header_row",
        dayHeaderClass: (info) =>
            joinClasses("o_calendar_header_cell", info.inPopover && "p-1 ps-3 fw-bold"),
        dayHeaderInnerClass: "o_calendar_header_cell_inner d-flex align-items-center",

        /* Day cell */

        dayRowClass: "o_calendar_day_row",
        dayCellClass: (info) =>
            joinClasses("o_calendar_day", info.isOther && "o_calendar_day_other"),
        dayCellTopClass: "o_calendar_day_top d-flex flex-column align-items-center",
        dayCellTopInnerClass: "o_calendar_day_top_number rounded-circle text-center",
        dayCellInnerClass: (info) =>
            joinClasses("o_calendar_day_events", info.inPopover && "overflow-auto"),
        inlineWeekNumberClass:
            "o_calendar_week_number position-absolute top-0 start-0 px-1 lh-sm text-muted smaller",

        /* Misc */

        highlightClass: "o_calendar_fill o_calendar_highlight",
        nonBusinessHoursClass: "o_calendar_fill o_calendar_non_business",
        nowIndicatorLineClass: "o_calendar_now_line pe-none",
        nowIndicatorHeaderClass: "d-none",
    },
    views: {
        dayGrid: {
            ...borderedGridClasses,
            dayHeaderInnerClass: (info) => !info.inPopover && "text-uppercase smaller",
            rowEventClass: "px-1",
        },
        multiMonth: {
            singleMonthClass: (info) =>
                joinClasses(
                    "o_calendar_month p-2",
                    info.multiMonthColumns === 1 && "o_calendar_month_sticky"
                ),
            singleMonthHeaderClass: "o_calendar_month_header",
            singleMonthHeaderInnerClass: "o_calendar_month_title mb-1 cursor-default",
            tableClass: "o_calendar_month_table",
            tableHeaderClass: "o_calendar_month_table_header",
            tableBodyClass: "o_calendar_month_body",
            // FullCalendar sizes the multi-day fills (events, selection) with 1px borders between
            // the days
            dayHeaderClass: "border cursor-default",
            dayHeaderInnerClass: "text-uppercase smaller",
            dayCellClass: "border",
            dayCellTopClass: "justify-content-center cursor-pointer",
            dayCellInnerClass: "d-none",
        },
        timeGrid: {
            ...borderedGridClasses,
            dayLaneClass: "o_calendar_lane border",
            slotLaneClass: (info) =>
                joinClasses(
                    "o_calendar_time_slot border",
                    info.isMinor && "o_calendar_time_slot_minor border-top-0"
                ),
            slotHeaderClass: (info) =>
                joinClasses(
                    "o_calendar_time_slot_label justify-content-end",
                    info.isMinor && "o_calendar_time_slot_minor"
                ),
            slotHeaderInnerClass: "o_calendar_time_slot_label_inner px-1",
            // not stretched: FullCalendar measures its height as a width of the time axis
            weekNumberHeaderClass: "o_calendar_week_number_header align-items-center",
            weekNumberHeaderInnerClass: "opacity-0",
            allDayDividerClass: "o_calendar_all_day_divider position-relative p-0",
            // lines between the time axis and the days, and below the day headers
            slotHeaderDividerClass: "border-end",
            dayHeaderDividerClass: "border-bottom",
            // keep some room in the all-day row to be able to click it when empty
            dayCellInnerClass: "mb-3",
            eventInnerClass: "m-1 my-md-0",
        },
        timeGridWeek: {
            dayHeaderInnerClass: "flex-column text-uppercase smaller",
        },
        timeGridDay: {
            dayHeaderInnerClass: "gap-1 ms-1",
        },
    },
};
