import { click, drag, edit, hover, queryFirst, queryRect } from "@odoo/hoot-dom";
import { advanceFrame, advanceTime, animationFrame } from "@odoo/hoot-mock";
import { EventBus } from "@odoo/owl";
import { contains, getMockEnv, swipeLeft, swipeRight } from "@web/../tests/web_test_helpers";

import { createElement } from "@web/core/utils/xml";
import { CalendarModel } from "@web/views/calendar/calendar_model";
import { Field } from "@web/views/fields/field";

export const DEFAULT_DATE = luxon.DateTime.local(2021, 7, 16, 8, 0, 0, 0);

export const FAKE_RECORDS = {
    1: {
        id: 1,
        title: "1 day, all day in July",
        start: DEFAULT_DATE,
        isAllDay: true,
        end: DEFAULT_DATE,
    },
    2: {
        id: 2,
        title: "3 days, all day in July",
        start: DEFAULT_DATE.plus({ days: 2 }),
        isAllDay: true,
        end: DEFAULT_DATE.plus({ days: 4 }),
    },
    3: {
        id: 3,
        title: "1 day, all day in June",
        start: DEFAULT_DATE.plus({ months: -1 }),
        isAllDay: true,
        end: DEFAULT_DATE.plus({ months: -1 }),
    },
    4: {
        id: 4,
        title: "3 days, all day in June",
        start: DEFAULT_DATE.plus({ months: -1, days: 2 }),
        isAllDay: true,
        end: DEFAULT_DATE.plus({ months: -1, days: 4 }),
    },
    5: {
        id: 5,
        title: "Over June and July",
        start: DEFAULT_DATE.startOf("month").plus({ days: -2 }),
        isAllDay: true,
        end: DEFAULT_DATE.startOf("month").plus({ days: 2 }),
    },
};

export const FAKE_FILTER_SECTIONS = [
    {
        label: "Attendees",
        fieldName: "partner_ids",
        avatar: {
            model: "res.partner",
            field: "avatar_128",
        },
        hasAvatar: true,
        write: {
            model: "filter_partner",
            field: "partner_id",
        },
        canAddFilter: true,
        filters: [
            {
                type: "user",
                label: "Mitchell Admin",
                active: true,
                value: 3,
                colorIndex: 3,
                recordId: null,
                canRemove: false,
                hasAvatar: true,
            },
            {
                type: "record",
                label: "Brandon Freeman",
                active: true,
                value: 4,
                colorIndex: 4,
                recordId: 1,
                canRemove: true,
                hasAvatar: true,
            },
            {
                type: "record",
                label: "Marc Demo",
                active: false,
                value: 6,
                colorIndex: 6,
                recordId: 2,
                canRemove: true,
                hasAvatar: true,
            },
        ],
    },
    {
        label: "Users",
        fieldName: "user_id",
        avatar: {
            model: null,
            field: null,
        },
        hasAvatar: false,
        write: {
            model: null,
            field: null,
        },
        canAddFilter: false,
        filters: [
            {
                type: "record",
                label: "Brandon Freeman",
                active: false,
                value: 1,
                colorIndex: false,
                recordId: null,
                canRemove: true,
                hasAvatar: true,
            },
            {
                type: "record",
                label: "Marc Demo",
                active: false,
                value: 2,
                colorIndex: false,
                recordId: null,
                canRemove: true,
                hasAvatar: true,
            },
        ],
    },
];

export const FAKE_FIELDS = {
    id: { string: "Id", type: "integer" },
    user_id: { string: "User", type: "many2one", relation: "user", default: -1 },
    partner_id: {
        string: "Partner",
        type: "many2one",
        relation: "partner",
        related: "user_id.partner_id",
        default: 1,
    },
    name: { string: "Name", type: "char" },
    description: { string: "Description", type: "html" },
    start_date: { string: "Start Date", type: "date" },
    stop_date: { string: "Stop Date", type: "date" },
    start: { string: "Start Datetime", type: "datetime" },
    stop: { string: "Stop Datetime", type: "datetime" },
    delay: { string: "Delay", type: "float" },
    allday: { string: "Is All Day", type: "boolean" },
    partner_ids: {
        string: "Attendees",
        type: "one2many",
        relation: "partner",
        default: [[6, 0, [1]]],
    },
    type: { string: "Type", type: "integer" },
    event_type_id: { string: "Event Type", type: "many2one", relation: "event_type" },
    color: { string: "Color", type: "integer", related: "event_type_id.color" },
};

export const FAKE_MODEL = {
    bus: new EventBus(),
    canCreate: true,
    canDelete: true,
    canEdit: true,
    date: DEFAULT_DATE,
    fieldMapping: {
        date_start: "start_date",
        date_stop: "stop_date",
        date_delay: "delay",
        all_day: "allday",
        color: "color",
    },
    fieldNames: ["start_date", "stop_date", "color", "delay", "allday", "user_id"],
    fields: FAKE_FIELDS,
    filterSections: FAKE_FILTER_SECTIONS,
    firstDayOfWeek: 0,
    isDateHidden: false,
    isTimeHidden: false,
    hasAllDaySlot: true,
    hasEditDialog: false,
    quickCreate: false,
    popoverFieldNodes: {
        name: Field.parseFieldNode(
            createElement("field", { name: "name" }),
            { event: { fields: FAKE_FIELDS } },
            "event",
            "calendar"
        ),
        description: Field.parseFieldNode(
            createElement("field", { name: "description" , class: "text-wrap"}),
            { event: { fields: FAKE_FIELDS } },
            "event",
            "calendar"
        ),
    },
    activeFields: {
        name: {
            context: "{}",
            invisible: false,
            readonly: false,
            required: false,
            onChange: false,
        },
        description: {
            context: "{}",
            invisible: false,
            readonly: false,
            required: false,
            onChange: false,
        },
    },
    rangeEnd: DEFAULT_DATE.endOf("month"),
    rangeStart: DEFAULT_DATE.startOf("month"),
    records: FAKE_RECORDS,
    resModel: "event",
    scale: "month",
    scales: ["day", "week", "month", "year"],
    unusualDays: [],
    load() {},
    createFilter() {},
    createRecord() {},
    unlinkFilter() {},
    unlinkRecord() {},
    updateFilter() {},
    updateRecord() {},
};

// DOM Utils
//------------------------------------------------------------------------------

/**
 * @param {HTMLElement} element
 */
function instantScrollTo(element) {
    element.scrollIntoView({ behavior: "instant", block: "center" });
}

/**
 * @param {string} date
 * @returns {HTMLElement}
 */
export function findAllDaySlot(date) {
    return queryFirst(`.fc-daygrid-body .fc-day[data-date="${date}"]`);
}

/**
 * @param {string} date
 * @returns {HTMLElement}
 */
export function findDateCell(date) {
    return queryFirst(`.fc-day[data-date="${date}"]`);
}

/**
 * @param {number} eventId
 * @returns {HTMLElement}
 */
export function findEvent(eventId) {
    return queryFirst(`.o_event[data-event-id="${eventId}"]`);
}

/**
 * @param {string} date
 * @returns {HTMLElement}
 */
export function findDateColumn(date) {
    return queryFirst(`.fc-col-header-cell.fc-day[data-date="${date}"]`);
}

/**
 * @param {string} time
 * @returns {HTMLElement}
 */
export function findTimeRow(time) {
    return queryFirst(`.fc-timegrid-slot[data-time="${time}"]:eq(1)`);
}

/**
 * @param {string} sectionName
 * @returns {HTMLElement}
 */
export function findFilterPanelSection(sectionName) {
    return queryFirst(`.o_calendar_filter[data-name="${sectionName}"]`);
}

/**
 * @param {string} sectionName
 * @param {string} filterValue
 * @returns {HTMLElement}
 */
export function findFilterPanelFilter(sectionName, filterValue) {
    const root = findFilterPanelSection(sectionName);
    return queryFirst(`.o_calendar_filter_item[data-value="${filterValue}"]`, { root });
}

/**
 * @param {string} sectionName
 * @returns {HTMLElement}
 */
export function findFilterPanelSectionFilter(sectionName) {
    const root = findFilterPanelSection(sectionName);
    return queryFirst(`.o_calendar_filter_items_checkall`, { root });
}

/**
 * @param {string} date
 * @returns {Promise<void>}
 */
export async function pickDate(date) {
    const day = date.split("-")[2];
    const iDay = parseInt(day, 10) - 1;
    await click(`.o_datetime_picker .o_date_item_cell:not(.o_out_of_range):eq(${iDay})`);
    await animationFrame();
}

/**
 * @param {string} date
 * @returns {Promise<void>}
 */
export async function clickAllDaySlot(date) {
    const slot = findAllDaySlot(date);

    instantScrollTo(slot);

    await click(slot);
    await animationFrame();
}

/**
 * @param {string} date
 * @returns {Promise<void>}
 */
export async function clickDate(date) {
    const cell = findDateCell(date);

    instantScrollTo(cell);

    await click(cell);
    await advanceTime(500);
}

/**
 * @param {number} eventId
 * @returns {Promise<void>}
 */
export async function clickEvent(eventId) {
    const eventEl = findEvent(eventId);

    instantScrollTo(eventEl);

    await click(eventEl);
    await advanceTime(500); // wait for the popover to open (debounced)
}

export function expandCalendarView() {
    // Expends Calendar view and FC too
    let tmpElement = queryFirst(".fc");
    do {
        tmpElement = tmpElement.parentElement;
        tmpElement.classList.add("h-100");
    } while (!tmpElement.classList.contains("o_view_controller"));
}

/**
 * @param {string} startDateTime
 * @param {string} endDateTime
 * @returns {Promise<void>}
 */
export async function selectTimeRange(startDateTime, endDateTime) {
    const [startDate, startTime] = startDateTime.split(" ");
    const [endDate, endTime] = endDateTime.split(" ");

    // Try to display both rows on the screen before drag'n'drop.
    const startHour = Number(startTime.slice(0, 2));
    const endHour = Number(endTime.slice(0, 2));
    const midHour = Math.floor((startHour + endHour) / 2);
    const midTime = `${String(midHour).padStart(2, "0")}:00:00`;

    instantScrollTo(
        queryFirst(`.fc-timegrid-slot[data-time="${midTime}"]:eq(1)`, { visible: false })
    );

    const startColumnRect = queryRect(`.fc-col-header-cell.fc-day[data-date="${startDate}"]`);
    const startRow = queryFirst(`.fc-timegrid-slot[data-time="${startTime}"]:eq(1)`);
    const endColumnRect = queryRect(`.fc-col-header-cell.fc-day[data-date="${endDate}"]`);
    const endRow = queryFirst(`.fc-timegrid-slot[data-time="${endTime}"]:eq(1)`);
    const optionStart = {
        relative: true,
        position: { y: 1, x: startColumnRect.left },
    };

    await hover(startRow, optionStart);
    await animationFrame();
    const { drop } = await drag(startRow, optionStart);
    await animationFrame();
    await drop(endRow, {
        position: { y: -1, x: endColumnRect.left },
        relative: true,
    });

    await animationFrame();
}

/**
 * @param {string} startDate
 * @param {string} endDate
 * @returns {Promise<void>}
 */
export async function selectDateRange(startDate, endDate) {
    const startCell = findDateCell(startDate);
    const endCell = findDateCell(endDate);

    instantScrollTo(startCell);

    await hover(startCell);
    await animationFrame();

    const { moveTo, drop } = await drag(startCell);
    await animationFrame();

    await moveTo(endCell);
    await animationFrame();

    await drop();
    await animationFrame();
}

/**
 * @param {string} startDate
 * @param {string} endDate
 * @returns {Promise<void>}
 */
export async function selectAllDayRange(startDate, endDate) {
    const start = findAllDaySlot(startDate);
    const end = findAllDaySlot(endDate);

    instantScrollTo(start);

    await hover(start);
    await animationFrame();

    const { drop } = await drag(start);
    await animationFrame();

    await drop(end);
    await animationFrame();
}
export async function closeCwPopOver() {
    if (getMockEnv().isSmall) {
        await contains(`.oi-arrow-left`).click();
    } else {
        await contains(`.o_cw_popover_close`).click();
    }
}
/**
 * @param {number} eventId
 * @param {string} date
 * @param {{ disableDrop: boolean }} [options]
 * @returns {Promise<void>}
 */
export async function moveEventToDate(eventId, date, options) {
    const eventEl = findEvent(eventId);
    const cell = findDateCell(date);

    instantScrollTo(eventEl);

    await hover(eventEl);
    await animationFrame();

    const { drop, moveTo } = await drag(eventEl);
    await animationFrame();

    await moveTo(cell);
    await animationFrame();

    if (!options?.disableDrop) {
        await drop();
    }

    await animationFrame();
    await animationFrame();
}

/**
 * @param {number} eventId
 * @param {string} dateTime
 * @returns {Promise<void>}
 */
export async function moveEventToTime(eventId, dateTime) {
    const eventEl = findEvent(eventId);
    const [date, time] = dateTime.split(" ");

    instantScrollTo(eventEl);

    const row = findTimeRow(time);
    const rowRect = queryRect(row);

    const column = findDateColumn(date);
    const columnRect = queryRect(column);

    const { drop, moveTo } = await drag(eventEl, {
        position: { y: 1 },
        relative: true,
    });

    if (getMockEnv().isSmall) {
        await advanceTime(500);
    }

    await animationFrame();

    await moveTo(row, {
        position: {
            y: rowRect.y + 1,
            x: columnRect.x + columnRect.width / 2,
        },
    });
    await animationFrame();

    await drop();
    await advanceFrame(5);
}

export async function selectHourOnPicker(selectedValue) {
    await click(".o_time_picker_input:eq(0)");
    await animationFrame();
    await edit(selectedValue, { confirm: "enter" });
    await animationFrame();
}

/**
 * @param {number} eventId
 * @param {string} date
 * @returns {Promise<void>}
 */
export async function moveEventToAllDaySlot(eventId, date) {
    const eventEl = findEvent(eventId);
    const slot = findAllDaySlot(date);

    instantScrollTo(eventEl);

    const columnRect = queryRect(eventEl);
    const slotRect = queryRect(slot);

    const { drop, moveTo } = await drag(eventEl, {
        position: { y: 1 },
        relative: true,
    });

    if (getMockEnv().isSmall) {
        await advanceTime(500);
    }

    await animationFrame();

    await moveTo(slot, {
        position: {
            x: columnRect.x + columnRect.width / 2,
            y: slotRect.y,
        },
    });
    await animationFrame();

    await drop();
    await advanceFrame(5);
}

/**
 * @param {number} eventId
 * @param {string} dateTime
 * @returns {Promise<void>}
 */
export async function resizeEventToTime(eventId, dateTime) {
    const eventEl = findEvent(eventId);

    instantScrollTo(eventEl);

    await hover(`.fc-event-main:first`, { root: eventEl });
    await animationFrame();

    const resizer = queryFirst(`.fc-event-resizer-end`, { root: eventEl });
    Object.assign(resizer.style, {
        display: "block",
        height: "1px",
        bottom: "0",
    });

    const [date, time] = dateTime.split(" ");

    const row = findTimeRow(time);

    const column = findDateColumn(date);
    const columnRect = queryRect(column);

    await (
        await drag(resizer)
    ).drop(row, {
        position: { x: columnRect.x, y: -1 },
        relative: true,
    });
    await advanceTime(500);
}

/**
 * @param {number} eventId
 * @param {string} date
 * @returns {Promise<void>}
 */
export async function resizeEventToDate(eventId, date) {
    const eventEl = findEvent(eventId);
    const slot = findAllDaySlot(date);

    instantScrollTo(eventEl);

    await hover(".fc-event-main", { root: eventEl });
    await animationFrame();

    // Show the resizer
    const resizer = queryFirst(".fc-event-resizer-end", { root: eventEl });
    Object.assign(resizer.style, { display: "block", height: "1px", bottom: "0" });

    instantScrollTo(slot);

    const rowRect = queryRect(resizer);

    // Find the date cell and calculate the positions for dragging
    const dateCell = findDateCell(date);
    const columnRect = queryRect(dateCell);

    // Perform the drag-and-drop operation
    await hover(resizer, {
        position: { x: 0 },
        relative: true,
    });
    await animationFrame();

    const { drop } = await drag(resizer);
    await animationFrame();

    await drop(dateCell, {
        position: { y: rowRect.y - columnRect.y },
        relative: true,
    });
    await advanceTime(500);
}

/**
 * @param {"day" | "week" | "month" | "year"} scale
 * @returns {Promise<void>}
 */
export async function changeScale(scale) {
    await contains(`.o_view_scale_selector .scale_button_selection`).click();
    await contains(`.o-dropdown--menu .o_scale_button_${scale}`).click();
}

export async function displayCalendarPanel() {
    if (getMockEnv().isSmall) {
        await contains(".o_calendar_container .o_other_calendar_panel").click();
    }
}

export async function hideCalendarPanel() {
    if (getMockEnv().isSmall) {
        await contains(".o_calendar_container .o_other_calendar_panel").click();
    }
}

/**
 * @param {"prev" | "next"} direction
 * @returns {Promise<void>}
 */
export async function navigate(direction) {
    if (getMockEnv().isSmall) {
        if (direction === "next") {
            await swipeLeft(".o_calendar_widget");
        } else {
            await swipeRight(".o_calendar_widget");
        }
        await advanceFrame(16);
    } else {
        await contains(`.o_calendar_navigation_buttons .o_calendar_button_${direction}`).click();
    }
}

/**
 * @param {string} sectionName
 * @param {string} filterValue
 * @returns {Promise<void>}
 */
export async function toggleFilter(sectionName, filterValue) {
    const otherCalendarPanel = queryFirst(".o_other_calendar_panel");
    if (otherCalendarPanel) {
        click(otherCalendarPanel);
        await animationFrame();
    }
    const root = findFilterPanelFilter(sectionName, filterValue);
    const input = queryFirst(`input`, { root });

    instantScrollTo(input);

    await click(input);
    await animationFrame();

    if (otherCalendarPanel) {
        await click(otherCalendarPanel);
        await animationFrame();
    }
    await advanceTime(CalendarModel.DEBOUNCED_LOAD_DELAY);
    await animationFrame();
}

/**
 * @param {string} sectionName
 * @returns {Promise<void>}
 */
export async function toggleSectionFilter(sectionName) {
    const otherCalendarPanel = queryFirst(".o_other_calendar_panel");
    if (otherCalendarPanel) {
        await click(otherCalendarPanel);
        await animationFrame();
    }
    const root = findFilterPanelSectionFilter(sectionName);
    const input = queryFirst(`input`, { root });

    instantScrollTo(input);

    await click(input);
    await animationFrame();

    if (otherCalendarPanel) {
        await click(otherCalendarPanel);
        await animationFrame();
    }
    await advanceTime(CalendarModel.DEBOUNCED_LOAD_DELAY);
    await animationFrame();
}

/**
 * @param {string} sectionName
 * @param {string} filterValue
 * @returns {Promise<void>}
 */
export async function removeFilter(sectionName, filterValue) {
    const root = findFilterPanelFilter(sectionName, filterValue);
    const button = queryFirst(`.o_remove`, { root });

    instantScrollTo(button);

    await click(button);
    await advanceTime(CalendarModel.DEBOUNCED_LOAD_DELAY);
    await animationFrame();
}
