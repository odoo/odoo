import { click, drag, hover, queryFirst, queryRect } from "@odoo/hoot-dom";
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import { EventBus } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

import { createElement } from "@web/core/utils/xml";
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
        canCollapse: true,
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
                type: "all",
                label: "Everybody's calendar",
                active: false,
                value: "all",
                colorIndex: null,
                recordId: null,
                canRemove: false,
                hasAvatar: false,
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
        canCollapse: false,
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
    },
    activeFields: {
        name: {
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
    const event = findEvent(eventId);
    instantScrollTo(event);
    await click(event);
    await advanceTime(500); // wait for the popover to open (debounced)
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

    const { drop } = await drag(startRow, {
        position: { y: 1, x: startColumnRect.left },
        relative: true,
    });
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
    await (await drag(startCell)).drop(endCell);
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
    await (await drag(start)).drop(end);
    await animationFrame();
}

/**
 * @param {number} eventId
 * @param {string} date
 * @param {{ disableDrop: boolean }} [options]
 * @returns {Promise<void>}
 */
export async function moveEventToDate(eventId, date, options = {}) {
    const event = findEvent(eventId);
    const cell = findDateCell(date);

    instantScrollTo(event);
    const { drop } = await (await drag(event)).moveTo(cell);

    if (!options.disableDrop) {
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
    const event = findEvent(eventId);
    const [date, time] = dateTime.split(" ");
    const columnRect = queryRect(findDateColumn(date));
    const row = findTimeRow(time);

    instantScrollTo(event);
    await (
        await drag(event, {
            position: { y: 0, x: 0 },
            relative: true,
        })
    ).drop(row, {
        position: { y: 0, x: columnRect.x },
        relative: true,
    });
    await animationFrame();
}

/**
 * @param {number} eventId
 * @param {string} date
 * @returns {Promise<void>}
 */
export async function moveEventToAllDaySlot(eventId, date) {
    const event = findEvent(eventId);
    const slot = findAllDaySlot(date);

    instantScrollTo(event);
    await (await drag(event)).drop(slot);
    await animationFrame();
}

/**
 * @param {number} eventId
 * @param {string} dateTime
 * @returns {Promise<void>}
 */
export async function resizeEventToTime(eventId, dateTime) {
    const event = findEvent(eventId);
    instantScrollTo(event);
    await hover(queryFirst(`.fc-event-main`, { root: event }));
    await animationFrame();

    const resizer = queryFirst(`.fc-event-resizer-end`, { root: event });
    Object.assign(resizer.style, { display: "block", height: "1px", bottom: "0" });
    const [date, time] = dateTime.split(" ");
    const columnRect = queryRect(findDateColumn(date));
    const row = findTimeRow(time);

    await (
        await drag(resizer, {
            position: { y: 0, x: 0 },
            relative: true,
        })
    ).drop(row, {
        position: { y: -1, x: columnRect.x },
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
    const event = findEvent(eventId);
    const slot = findAllDaySlot(date);

    instantScrollTo(event);
    await hover(queryFirst(".fc-event-main", { root: event }));
    await animationFrame();

    // Show the resizer
    const resizer = queryFirst(".fc-event-resizer-end", { root: event });
    Object.assign(resizer.style, { display: "block", height: "1px", bottom: "0" });

    instantScrollTo(slot);

    // Find the date cell and calculate the positions for dragging
    const dateCell = findDateCell(date);
    const columnRect = queryRect(dateCell);
    const startRow = queryRect(resizer);

    // Perform the drag-and-drop operation
    await (
        await drag(resizer, {
            position: { y: 0, x: 0 },
            relative: true,
        })
    ).drop(dateCell, {
        position: { y: startRow.y - columnRect.y, x: 0 },
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

/**
 * @param {"prev" | "next"} direction
 * @returns {Promise<void>}
 */
export async function navigate(direction) {
    await contains(`.o_calendar_navigation_buttons .o_calendar_button_${direction}`).click();
}

/**
 * @param {string} sectionName
 * @param {string} filterValue
 * @returns {Promise<void>}
 */
export async function toggleFilter(sectionName, filterValue) {
    const root = findFilterPanelFilter(sectionName, filterValue);
    const input = queryFirst(`input`, { root });
    instantScrollTo(input);
    await click(input);
    await animationFrame();
}

/**
 * @param {string} sectionName
 * @returns {Promise<void>}
 */
export async function toggleSectionFilter(sectionName) {
    const root = findFilterPanelSectionFilter(sectionName);
    const input = queryFirst(`input`, { root });
    instantScrollTo(input);
    await click(input);
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
    await animationFrame();
}
