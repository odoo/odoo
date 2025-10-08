import { beforeEach, expect, test } from "@odoo/hoot";
import {
    Deferred,
    advanceTime,
    animationFrame,
    click,
    hover,
    pointerDown,
    pointerUp,
    press,
    queryAllRects,
    queryAllTexts,
    queryFirst,
    queryOne,
    queryRect,
    runAllTimers,
} from "@odoo/hoot-dom";
import { mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { Component, onRendered, onWillStart, xml } from "@odoo/owl";
import {
    MockServer,
    contains,
    defineActions,
    defineModels,
    defineParams,
    fields,
    getMockEnv,
    getService,
    makeServerError,
    mockService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    preloadBundle,
    serverState,
    validateSearch,
} from "@web/../tests/web_test_helpers";
import {
    changeScale,
    clickAllDaySlot,
    clickDate,
    clickEvent,
    closeCwPopOver,
    displayCalendarPanel,
    expandCalendarView,
    hideCalendarPanel,
    moveEventToAllDaySlot,
    moveEventToDate,
    moveEventToTime,
    navigate,
    pickDate,
    removeFilter,
    resizeEventToDate,
    resizeEventToTime,
    selectAllDayRange,
    selectDateRange,
    selectHourOnPicker,
    selectTimeRange,
    toggleFilter,
    toggleSectionFilter,
} from "./calendar_test_helpers";

import { registry } from "@web/core/registry";
import { zip } from "@web/core/utils/arrays";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { calendarView } from "@web/views/calendar/calendar_view";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";
import { WebClient } from "@web/webclient/webclient";

class Event extends models.Model {
    name = fields.Char();
    type_id = fields.Many2one({ string: "Event Type", relation: "event.type" });
    start_date = fields.Date({ compute: "_compute_start_date", store: true, readonly: false });
    stop_date = fields.Date({ compute: "_compute_stop_date", store: true, readonly: false });
    start = fields.Datetime();
    stop = fields.Datetime();
    delay = fields.Float();
    is_all_day = fields.Boolean();
    user_id = fields.Many2one({ relation: "calendar.users", default: serverState.userId });
    partner_id = fields.Many2one({ relation: "calendar.partner", related: "user_id.partner_id" });
    attendee_ids = fields.One2many({ relation: "calendar.partner", default: [[6, 0, [1]]] });
    color = fields.Integer({ related: "type_id.color" });
    is_hatched = fields.Boolean();
    is_striked = fields.Boolean();

    has_access() {
        return true;
    }

    _compute_start_date() {
        for (const record of this) {
            record.start_date = record.start && record.start.split(" ")[0];
        }
    }

    _compute_stop_date() {
        for (const record of this) {
            record.stop_date = record.stop && record.stop.split(" ")[0];
        }
    }

    _records = [
        {
            id: 1,
            name: "event 1",
            start: "2016-12-11 00:00:00",
            stop: "2016-12-11 00:00:00",
            user_id: serverState.userId,
            partner_id: 1,
            attendee_ids: [1, 2, 3],
        },
        {
            id: 2,
            name: "event 2",
            start: "2016-12-12 10:55:05",
            stop: "2016-12-12 14:55:05",
            user_id: serverState.userId,
            partner_id: 1,
            attendee_ids: [1, 2],
        },
        {
            id: 3,
            name: "event 3",
            start: "2016-12-12 15:55:05",
            stop: "2016-12-12 16:55:05",
            user_id: 4,
            partner_id: 4,
            attendee_ids: [1],
            is_hatched: true,
        },
        {
            id: 4,
            name: "event 4",
            start: "2016-12-14 15:55:05",
            stop: "2016-12-14 18:55:05",
            is_all_day: true,
            user_id: serverState.userId,
            partner_id: 1,
            attendee_ids: [1],
            is_striked: true,
        },
        {
            id: 5,
            name: "event 5",
            start: "2016-12-13 15:55:05",
            stop: "2016-12-20 18:55:05",
            user_id: 4,
            partner_id: 4,
            attendee_ids: [2, 3],
            is_hatched: true,
        },
        {
            id: 6,
            name: "event 6",
            start: "2016-12-18 08:00:00",
            stop: "2016-12-18 09:00:00",
            user_id: serverState.userId,
            partner_id: 1,
            attendee_ids: [3],
            is_hatched: true,
        },
        {
            id: 7,
            name: "event 7",
            start: "2016-11-14 08:00:00",
            stop: "2016-11-16 17:00:00",
            user_id: serverState.userId,
            partner_id: 1,
            attendee_ids: [2],
        },
    ];

    _views = {
        form: `
            <form>
                <field name="name"/>
                <field name="is_all_day"/>
                <group invisible="is_all_day">
                    <field name="start"/>
                    <field name="stop"/>
                </group>
                <group invisible="not is_all_day">
                    <field name="start_date"/>
                    <field name="stop_date"/>
                </group>
            </form>
        `,
        "form,1": `
            <form>
                <field name="is_all_day" invisible="1"/>
                <field name="start" invisible="not is_all_day"/>
                <field name="stop" invisible="is_all_day"/>
            </form>
        `,
    };
}

class EventType extends models.Model {
    _name = "event.type";

    name = fields.Char();
    color = fields.Integer();

    has_access() {
        return true;
    }

    _records = [
        { id: 1, name: "Event Type 1", color: 1 },
        { id: 2, name: "Event Type 2", color: 2 },
        { id: 3, name: "Event Type 3 (color 4)", color: 4 },
    ];
}

class CalendarUsers extends models.Model {
    _name = "calendar.users";

    name = fields.Char();
    partner_id = fields.Many2one({ relation: "calendar.partner" });
    image = fields.Char();

    _records = [
        { id: serverState.userId, name: "user 1", partner_id: 1 },
        { id: 4, name: "user 4", partner_id: 4 },
    ];
}

class CalendarPartner extends models.Model {
    _name = "calendar.partner";

    name = fields.Char();
    image = fields.Char();

    _records = [
        { id: 1, name: "partner 1", image: "AAA" },
        { id: 2, name: "partner 2", image: "BBB" },
        { id: 3, name: "partner 3", image: "CCC" },
        { id: 4, name: "partner 4", image: "DDD" },
    ];
}

class FilterPartner extends models.Model {
    _name = "filter.partner";

    user_id = fields.Many2one({ relation: "calendar.users" });
    partner_id = fields.Many2one({ relation: "calendar.partner" });
    is_checked = fields.Boolean();

    _records = [
        { id: 1, user_id: serverState.userId, partner_id: 1, is_checked: true },
        { id: 2, user_id: serverState.userId, partner_id: 2, is_checked: true },
        { id: 3, user_id: 4, partner_id: 3, is_checked: false },
    ];
}

defineModels([Event, EventType, CalendarUsers, CalendarPartner, FilterPartner]);
preloadBundle("web.fullcalendar_lib");
beforeEach(() => {
    mockDate("2016-12-12T08:00:00", 1);
    const patchFullCalendarOptions = () => ({
        get options() {
            return Object.assign({}, super.options, {
                longPressDelay: 0,
                selectLongPressDelay: 0,
            });
        },
    });
    patchWithCleanup(CalendarYearRenderer.prototype, patchFullCalendarOptions());
    patchWithCleanup(CalendarCommonRenderer.prototype, patchFullCalendarOptions());
});

onRpc("has_group", () => true);

/**
 * @param {import("@odoo/hoot-dom").Target} from
 * @param {import("@odoo/hoot-dom").Target} to
 * @param {{
 *  start: "top" | "center" | "bottom";
 *  end: "top" | "center" | "bottom";
 * }} [positions] specify where the touches will occur in the start and end elements
 *  (default: `"center"` for both)
 * @returns {Promise<void>}
 */
async function selectRange(from, to, positions) {
    const startTarget = queryFirst(from);

    const startRect = queryRect(startTarget);
    const startPosition = {
        x: startRect.width / 2,
        y: 0,
    };
    if (positions?.start === "top") {
        startPosition.y += 1;
    } else if (positions?.start === "bottom") {
        startPosition.y += startRect.height - 1;
    } else {
        startPosition.y += startRect.height / 2;
    }

    const endRect = queryRect(to);
    const endPosition = {
        x: endRect.width / 2,
        y: 0,
    };
    if (positions?.end === "top") {
        endPosition.y += 1;
    } else if (positions?.end === "bottom") {
        endPosition.y += endRect.height - 1;
    } else {
        endPosition.y += endRect.height / 2;
    }

    await pointerDown(startTarget, {
        position: startPosition,
        relative: true,
    });
    await animationFrame();

    await hover(to, {
        position: endPosition,
        relative: true,
    });
    await animationFrame();

    await pointerUp(to, {
        position: endPosition,
        relative: true,
    });
    await animationFrame();
}

function expectEventToBeOver(eventSelector, ranges) {
    const eventRects = queryAllRects(eventSelector);
    expect(eventRects.length).toBe(ranges.length);

    let result = true;
    for (const [[start, end], eventRect] of zip(ranges, eventRects)) {
        const startDateRect = queryRect`.fc-daygrid-day[data-date="${start}"]`;
        const endDateRect = queryRect`.fc-daygrid-day[data-date="${end}"]`;
        const minX = startDateRect.left;
        const maxX = endDateRect.right;
        result &&=
            eventRect.left >= minX &&
            eventRect.left <= maxX &&
            eventRect.right >= minX &&
            eventRect.right <= maxX;
    }
    expect(result).toBe(true);
}

const checkFilterItems = async (amount) => {
    await displayCalendarPanel();
    expect(`.o_calendar_filter_item`).toHaveCount(amount);
    await hideCalendarPanel();
};

test.tags("desktop");
test(`simple calendar rendering on desktop`, async () => {
    Event._fields.partner_id = fields.Many2one({ relation: "calendar.partner" });
    Event._records.push(
        {
            id: 8,
            user_id: serverState.userId,
            partner_id: false,
            name: "event 7",
            start: "2016-12-18 09:00:00",
            stop: "2016-12-18 10:00:00",
            attendee_ids: [2],
        },
        {
            id: 9,
            user_id: serverState.userId,
            partner_id: false,
            name: "event 8",
            start: "2016-12-11 05:15:00",
            stop: "2016-12-11 05:30:00",
            attendee_ids: [1, 2, 3],
            delay: 0.25,
        }
    );

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="is_all_day" mode="week" attendee="attendee_ids" color="partner_id" date_delay="delay">
                <filter name="user_id" avatar_field="image"/>
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="partner_id" filters="1" invisible="1"/>
                <field name="delay" invisible="1"/>
            </calendar>
        `,
    });

    // test events in different scale
    expect(`.o_calendar_renderer .fc-view`).toHaveCount(1);
    expect(`.o_event`).toHaveCount(0, {
        message: "By default, only the events of the current user are displayed (0 in this case)",
    });

    await toggleSectionFilter("attendee_ids");
    expect(`.o_event`).toHaveCount(6, {
        message: "should display 6 events on the week (4 event + 1 is_all_day + 1 >24h is_all_day)",
    });
    expect(`.o_event_oneliner`).toHaveCount(1, {
        message: "should contain 1 oneliner event (the one we add)",
    });

    await changeScale("day");
    expect(`.o_event`).toHaveCount(2);
    expect(`.o_calendar_sidebar .o_datetime_picker .o_selected`).toHaveCount(1);

    await changeScale("month");
    await toggleSectionFilter("attendee_ids");
    await toggleFilter("attendee_ids", "1");
    await toggleFilter("attendee_ids", "2");
    expect(`.o_event`).toHaveCount(8, {
        message:
            "should display 7 events on the month (6 events + 2 week event - 1 'event 6' is filtered + 1 'Undefined event')",
    });

    // test filters
    expect(`.o_calendar_sidebar .o_calendar_filter`).toHaveCount(2);
    expect(`.o_calendar_filter:eq(1)`).toBeVisible();
    expect(`.o_calendar_filter:eq(1) .o_calendar_filter_item`).toHaveCount(3);

    expect(`.o_calendar_filter:eq(1) .o_calendar_filter_item:eq(-1)`).not.toHaveAttribute(
        "data-value"
    );
    expect(`.o_calendar_filter:eq(1) .o_calendar_filter_item:eq(-1)`).toHaveText("Undefined");
    expect(`.o_calendar_filter:eq(1) .o_calendar_filter_item:eq(-1) label img`).toHaveCount(0);

    expect(`.o_calendar_filter:eq(0)`).toBeVisible();
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item`).toHaveCount(2);
    expect(`.o_calendar_filter:eq(0) .o-autocomplete`).toHaveCount(1);

    await toggleFilter("attendee_ids", "1");
    expect(`.o_event`).toHaveCount(6);

    await toggleFilter("attendee_ids", "2");
    expect(`.o_event`).toHaveCount(0);

    // test search bar in filter
    await contains(`.o_calendar_sidebar input[type=text]`).click();
    expect(`.dropdown-item`).toHaveCount(2);
    expect(queryAllTexts`.dropdown-item`).toEqual(["partner 3", "partner 4"]);

    await contains(`.dropdown-item:eq(0)`).click();
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item`).toHaveCount(3);

    await contains(`.o_calendar_sidebar input[type=text]`).click();
    expect(`.dropdown-item`).toHaveCount(1);
    expect(`.dropdown-item`).toHaveText("partner 4");

    await removeFilter("attendee_ids", "2");
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item`).toHaveCount(2);
});

test.tags("mobile");
test(`simple calendar rendering on mobile`, async () => {
    Event._fields.partner_id = fields.Many2one({ relation: "calendar.partner" });
    Event._records.push(
        {
            id: 8,
            user_id: serverState.userId,
            partner_id: false,
            name: "event 7",
            start: "2016-12-18 09:00:00",
            stop: "2016-12-18 10:00:00",
            attendee_ids: [2],
        },
        {
            id: 9,
            user_id: serverState.userId,
            partner_id: false,
            name: "event 8",
            start: "2016-12-11 05:15:00",
            stop: "2016-12-11 05:30:00",
            attendee_ids: [1, 2, 3],
            delay: 0.25,
        }
    );

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="is_all_day" mode="week" attendee="attendee_ids" color="partner_id" date_delay="delay">
                <filter name="user_id" avatar_field="image"/>
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="partner_id" filters="1" invisible="1"/>
                <field name="delay" invisible="1"/>
            </calendar>
        `,
    });

    // test events in different scale
    expect(`.o_calendar_renderer .fc-view`).toHaveCount(1);
    expect(`.o_event`).toHaveCount(0, {
        message: "By default, only the events of the current user are displayed (0 in this case)",
    });
    await toggleSectionFilter("attendee_ids");
    await changeScale("week");
    expect(`.o_event`).toHaveCount(6, {
        message: "should display 6 events on the week (4 event + 1 is_all_day + 1 >24h is_all_day)",
    });
    expect(`.o_event_oneliner`).toHaveCount(1, {
        message: "should contain 1 oneliner event (the one we add)",
    });

    await changeScale("day");
    expect(`.o_event`).toHaveCount(2);
    await changeScale("month");
    await toggleSectionFilter("attendee_ids");
    await toggleFilter("attendee_ids", "1");
    await toggleFilter("attendee_ids", "2");
    expect(`.o_event`).toHaveCount(8, {
        message:
            "should display 7 events on the month (6 events + 2 week event - 1 'event 6' is filtered + 1 'Undefined event')",
    });

    // test filters
    await displayCalendarPanel();
    expect(`.o_calendar_sidebar .o_calendar_filter`).toHaveCount(2);
    expect(`.o_calendar_filter:eq(1)`).toBeVisible();
    expect(`.o_calendar_filter:eq(1) .o_calendar_filter_item`).toHaveCount(3);

    expect(`.o_calendar_filter:eq(1) .o_calendar_filter_item:eq(-1)`).not.toHaveAttribute(
        "data-value"
    );
    expect(`.o_calendar_filter:eq(1) .o_calendar_filter_item:eq(-1)`).toHaveText("Undefined");
    expect(`.o_calendar_filter:eq(1) .o_calendar_filter_item:eq(-1) label img`).toHaveCount(0);

    expect(`.o_calendar_filter:eq(0)`).toBeVisible();
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item`).toHaveCount(2);
    expect(`.o_calendar_filter:eq(0) .o-autocomplete`).toHaveCount(1);
    await hideCalendarPanel();
    await toggleFilter("attendee_ids", "1");
    expect(`.o_event`).toHaveCount(6);

    await toggleFilter("attendee_ids", "2");
    expect(`.o_event`).toHaveCount(0);

    // test search bar in filter
    await displayCalendarPanel();
    await contains(`.o_calendar_sidebar input[type=text]`).click();
    expect(`.dropdown-item`).toHaveCount(2);
    expect(queryAllTexts`.dropdown-item`).toEqual(["partner 3", "partner 4"]);

    await contains(`.dropdown-item:eq(0)`).click();
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item`).toHaveCount(3);

    await contains(`.o_calendar_sidebar input[type=text]`).click();
    expect(`.dropdown-item`).toHaveCount(1);
    expect(`.dropdown-item`).toHaveText("partner 4");

    await removeFilter("attendee_ids", "2");
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item`).toHaveCount(2);
});

test(`filter panel autocomplete: updates when typing`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
            </calendar>
        `,
    });
    await displayCalendarPanel();
    const root = `.o_calendar_filter[data-name="attendee_ids"]`;
    expect(`${root} .o-autocomplete--dropdown-menu`).toHaveCount(0);
    expect(`${root} .o-autocomplete--dropdown-item`).toHaveCount(0);

    await contains(`${root} .o-autocomplete--input`).click();
    expect(`${root} .o-autocomplete--dropdown-menu`).toHaveCount(1);
    expect(`${root} .o-autocomplete--dropdown-item`).toHaveCount(2);
    expect(queryAllTexts(`${root} .o-autocomplete--dropdown-item`)).toEqual([
        "partner 3",
        "partner 4",
    ]);

    await contains(`${root} .o-autocomplete--input`).edit("partner 3", { confirm: false });
    await advanceTime(500);
    expect(`${root} .o-autocomplete--dropdown-menu`).toHaveCount(1);
    expect(`${root} .o-autocomplete--dropdown-item`).toHaveCount(1);
    expect(queryAllTexts(`${root} .o-autocomplete--dropdown-item`)).toEqual(["partner 3"]);

    await contains(`${root} .o-autocomplete--input`).edit(
        "a string that would yield to no result as it is too very much convoluted",
        { confirm: false }
    );
    await advanceTime(500);
    expect(`${root} .o-autocomplete--dropdown-menu`).toHaveCount(1);
    expect(`${root} .o-autocomplete--dropdown-item`).toHaveCount(1);
    expect(queryAllTexts(`${root} .o-autocomplete--dropdown-item`)).toEqual(["No records"]);
});

test(`check the avatar of the attendee in the calendar filter panel`, async () => {
    CalendarPartner._views = {
        list: `<list><field name="name"/></list>`,
        kanban: `<kanban><templates><t name="card"><field name="name"/></t></templates></kanban>`,
    };
    CalendarPartner._records.push(
        { id: 5, name: "foo partner 5" },
        { id: 6, name: "foo partner 6" },
        { id: 7, name: "foo partner 7" },
        { id: 8, name: "foo partner 8" },
        { id: 9, name: "foo partner 9" },
        { id: 10, name: "foo partner 10" },
        { id: 11, name: "foo partner 11" },
        { id: 12, name: "foo partner 12" },
        { id: 13, name: "foo partner 13" }
    );

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id" avatar_field="avatar_128"/>
            </calendar>
        `,
    });
    await displayCalendarPanel();
    const section = `.o_calendar_filter[data-name="attendee_ids"]`;

    expect(`.o_calendar_sidebar .o_calendar_filter`).toHaveCount(1);
    expect(`.o_calendar_filter:eq(0) .o-autocomplete`).toHaveCount(1);
    expect(".o_calendar_filter_item:eq(-2)").not.toHaveText("partner 3");

    expect(`${section} .o-autocomplete--dropdown-menu`).toHaveCount(0);
    expect(`${section} .o-autocomplete--dropdown-item`).toHaveCount(0);
    await contains(`${section} .o-autocomplete--input`).click();
    await runAllTimers();
    expect(".o-autocomplete--dropdown-item:first-child").toHaveText("partner 3");
    expect(`.o-autocomplete--dropdown-item:first-child .dropdown-item img`).toHaveClass("o_avatar");

    await contains(".o-autocomplete--dropdown-item:first-child").click();
    expect(".o_calendar_filter_item:eq(-1)").toHaveText("partner 3");
});

test.tags("desktop");
test(`Select multiple attendees in the calendar filter panel autocomplete on desktop`, async () => {
    CalendarPartner._views = {
        list: `<list><field name="name"/></list>`,
    };
    CalendarPartner._records.push(
        { id: 5, name: "foo partner 5" },
        { id: 6, name: "foo partner 6" },
        { id: 7, name: "foo partner 7" },
        { id: 8, name: "foo partner 8" },
        { id: 9, name: "foo partner 9" },
        { id: 10, name: "foo partner 10" },
        { id: 11, name: "foo partner 11" },
        { id: 12, name: "foo partner 12" },
        { id: 13, name: "foo partner 13" },
        { id: 14, name: "foo partner 14" }
    );

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
            </calendar>
        `,
    });

    const section = `.o_calendar_filter[data-name="attendee_ids"]`;
    expect(`.o_calendar_sidebar .o_calendar_filter`).toHaveCount(1);
    await checkFilterItems(2);
    expect(queryAllTexts`.o_calendar_filter_item`).toEqual(["partner 1", "partner 2"]);

    expect(`.o_calendar_filter:eq(0) .o-autocomplete`).toHaveCount(1);
    await contains(`${section} .o-autocomplete--input`).click();
    await runAllTimers();
    expect(`.dropdown-item`).toHaveCount(9);
    expect(queryAllTexts`.o-autocomplete--dropdown-item`).toEqual([
        "partner 3",
        "partner 4",
        "foo partner 5",
        "foo partner 6",
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "Search More...",
    ]);

    await contains(`.o-autocomplete--dropdown-item:last-child`).click();
    expect(`.modal .o_data_row`).toHaveCount(12);
    await contains(".o_data_row:nth-child(1) .o_list_record_selector").click();
    await contains(".o_data_row:nth-child(2) .o_list_record_selector").click();
    await contains(".o_dialog .o_select_button").click();
    expect("o_dialog").toHaveCount(0);

    expect(`.o_calendar_sidebar .o_calendar_filter`).toHaveCount(1);
    await checkFilterItems(4);
    expect(queryAllTexts`.o_calendar_filter_item`).toEqual([
        "partner 1",
        "partner 2",
        "partner 3",
        "partner 4",
    ]);
});

test.tags("desktop");
test(`add a filter with the search more dialog on desktop`, async () => {
    CalendarPartner._views = {
        list: `<list><field name="name"/></list>`,
    };
    CalendarPartner._records.push(
        { id: 5, name: "foo partner 5" },
        { id: 6, name: "foo partner 6" },
        { id: 7, name: "foo partner 7" },
        { id: 8, name: "foo partner 8" },
        { id: 9, name: "foo partner 9" },
        { id: 10, name: "foo partner 10" },
        { id: 11, name: "foo partner 11" },
        { id: 12, name: "foo partner 12" },
        { id: 13, name: "foo partner 13" },
        { id: 14, name: "foo partner 14" }
    );

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
            </calendar>
        `,
    });
    const section = `.o_calendar_filter[data-name="attendee_ids"]`;
    expect(`${section} .o_calendar_filter_item`).toHaveCount(2);
    expect(queryAllTexts`.o_calendar_filter_item`).toEqual(["partner 1", "partner 2"]);

    // Open the autocomplete dropdown
    expect(`${section} .o-autocomplete--dropdown-menu`).toHaveCount(0);
    expect(`${section} .o-autocomplete--dropdown-item`).toHaveCount(0);
    await contains(`${section} .o-autocomplete--input`).click();
    await advanceTime(500);
    expect(`${section} .o-autocomplete--dropdown-menu`).toHaveCount(1);
    expect(`${section} .o-autocomplete--dropdown-item`).toHaveCount(9);
    expect(queryAllTexts`.o-autocomplete--dropdown-item`).toEqual([
        "partner 3",
        "partner 4",
        "foo partner 5",
        "foo partner 6",
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "Search More...",
    ]);

    // Change the search term
    await contains(`.o-autocomplete--input`).edit("foo", { confirm: false });
    await advanceTime(500);
    expect(`${section} .o-autocomplete--dropdown-menu`).toHaveCount(1);
    expect(`${section} .o-autocomplete--dropdown-item`).toHaveCount(9);
    expect(queryAllTexts`.o-autocomplete--dropdown-item`).toEqual([
        "foo partner 5",
        "foo partner 6",
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "foo partner 11",
        "foo partner 12",
        "Search More...",
    ]);

    // Open the search more dialog
    expect(`.modal`).toHaveCount(0);
    await contains(`${section} .o-autocomplete--dropdown-item:last-child`).click();
    expect(`.modal`).toHaveCount(1);
    expect(`.modal .o_data_row`).toHaveCount(10);
    expect(queryAllTexts`.modal .o_data_row`).toEqual([
        "foo partner 5",
        "foo partner 6",
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "foo partner 11",
        "foo partner 12",
        "foo partner 13",
        "foo partner 14",
    ]);
    expect(`.modal .o_searchview_facet`).toHaveCount(1);
    expect(`.modal .o_searchview_facet`).toHaveText("Quick search: foo");

    // Choose a record
    await contains(".o_data_row:nth-child(1) .o_list_record_selector").click();
    await contains(".o_data_row:nth-child(2) .o_list_record_selector").click();
    await contains(".o_dialog .o_select_button").click();
    expect("o_dialog").toHaveCount(0);

    expect(`.o_calendar_sidebar .o_calendar_filter`).toHaveCount(1);
    await checkFilterItems(4);
    expect(queryAllTexts`.o_calendar_filter_item`).toEqual([
        "foo partner 5",
        "foo partner 6",
        "partner 1",
        "partner 2",
    ]);

    // Open the autocomplete dropdown
    expect(`${section} .o-autocomplete--dropdown-menu`).toHaveCount(0);
    expect(`${section} .o-autocomplete--dropdown-item`).toHaveCount(0);
    await contains(`${section} .o-autocomplete--input`).click();
    await advanceTime(500);
    expect(`${section} .o-autocomplete--dropdown-menu`).toHaveCount(1);
    expect(`${section} .o-autocomplete--dropdown-item`).toHaveCount(9);
    expect(queryAllTexts`.o-autocomplete--dropdown-item`).toEqual([
        "partner 3",
        "partner 4",
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "foo partner 11",
        "foo partner 12",
        "Search More...",
    ]);

    // Change the search term
    await contains(`.o-autocomplete--input`).edit("foo", { confirm: false });
    await advanceTime(500);
    expect(`${section} .o-autocomplete--dropdown-menu`).toHaveCount(1);
    expect(`${section} .o-autocomplete--dropdown-item`).toHaveCount(9);
    expect(queryAllTexts`.o-autocomplete--dropdown-item`).toEqual([
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "foo partner 11",
        "foo partner 12",
        "foo partner 13",
        "foo partner 14",
        "Search More...",
    ]);

    // Open the search more dialog
    expect(`.modal`).toHaveCount(0);
    await contains(`${section} .o-autocomplete--dropdown-item:last-child`).click();
    expect(`.modal`).toHaveCount(1);
    expect(`.modal .o_data_row`).toHaveCount(8);
    expect(queryAllTexts`.modal .o_data_row`).toEqual([
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "foo partner 11",
        "foo partner 12",
        "foo partner 13",
        "foo partner 14",
    ]);
    expect(`.modal .o_searchview_facet`).toHaveCount(1);
    expect(`.modal .o_searchview_facet`).toHaveText("Quick search: foo");

    // Close the search more dialog without choosing a record
    await contains(`.modal .o_form_button_cancel`).click();
    expect(`.modal`).toHaveCount(0);
    expect(`${section} .o_calendar_filter_item`).toHaveCount(4);
    expect(queryAllTexts`.o_calendar_filter_item`).toEqual([
        "foo partner 5",
        "foo partner 6",
        "partner 1",
        "partner 2",
    ]);
    expect(`.o-autocomplete--input`).toHaveValue("");
});

test.tags("desktop");
test(`add a filter with the search more dialog (field with a context)`, async () => {
    CalendarPartner._views = {
        list: `<list><field name="name"/></list>`,
    };
    CalendarPartner._records.push(
        { id: 5, name: "foo partner 5" },
        { id: 6, name: "foo partner 6" },
        { id: 7, name: "foo partner 7" },
        { id: 8, name: "foo partner 8" },
        { id: 9, name: "foo partner 9" },
        { id: 10, name: "foo partner 10" },
        { id: 11, name: "foo partner 11" },
        { id: 12, name: "foo partner 12" },
        { id: 13, name: "foo partner 13" },
        { id: 14, name: "foo partner 14" }
    );

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id" context="{'search_view_ref': 'my_view'}"/>
            </calendar>
        `,
    });

    onRpc("get_views", ({ kwargs }) => {
        expect.step("get_views");
        expect(kwargs.context.search_view_ref).toBe("my_view");
    });
    await contains(`.o_calendar_filter[data-name="attendee_ids"] .o-autocomplete--input`).click();
    await advanceTime(500);
    expect(
        `.o_calendar_filter[data-name="attendee_ids"] .o-autocomplete--dropdown-item:last-child`
    ).toHaveText("Search More...");
    await contains(
        `.o_calendar_filter[data-name="attendee_ids"] .o-autocomplete--dropdown-item:last-child`
    ).click();
    expect(`.modal`).toHaveCount(1);
    expect.verifySteps(["get_views"]);
});

test.tags("mobile");
test(`add a filter with the search more dialog on mobile`, async () => {
    CalendarPartner._views = {
        list: `<list><field name="name"/></list>`,
        kanban: `<kanban><templates><t t-name="card"><field class="o_data_row" name="name"/></t></templates></kanban>`,
    };
    CalendarPartner._records.push(
        { id: 5, name: "foo partner 5" },
        { id: 6, name: "foo partner 6" },
        { id: 7, name: "foo partner 7" },
        { id: 8, name: "foo partner 8" },
        { id: 9, name: "foo partner 9" },
        { id: 10, name: "foo partner 10" },
        { id: 11, name: "foo partner 11" },
        { id: 12, name: "foo partner 12" },
        { id: 13, name: "foo partner 13" },
        { id: 14, name: "foo partner 14" }
    );

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
            </calendar>
        `,
    });
    await displayCalendarPanel();
    const section = `.o_calendar_filter[data-name="attendee_ids"]`;
    expect(`${section} .o_calendar_filter_item`).toHaveCount(2);
    expect(queryAllTexts`.o_calendar_filter_item`).toEqual(["partner 1", "partner 2"]);

    // Open the autocomplete dropdown
    expect(`${section} .o-autocomplete--dropdown-menu`).toHaveCount(0);
    expect(`${section} .o-autocomplete--dropdown-item`).toHaveCount(0);
    await contains(`${section} .o-autocomplete--input`).click();
    await advanceTime(500);
    expect(`${section} .o-autocomplete--dropdown-menu`).toHaveCount(1);
    expect(`${section} .o-autocomplete--dropdown-item`).toHaveCount(9);
    expect(queryAllTexts`.o-autocomplete--dropdown-item`).toEqual([
        "partner 3",
        "partner 4",
        "foo partner 5",
        "foo partner 6",
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "Search More...",
    ]);

    // Change the search term
    await contains(`.o-autocomplete--input`).edit("foo", { confirm: false });
    await advanceTime(500);
    expect(`${section} .o-autocomplete--dropdown-menu`).toHaveCount(1);
    expect(`${section} .o-autocomplete--dropdown-item`).toHaveCount(9);
    expect(queryAllTexts`.o-autocomplete--dropdown-item`).toEqual([
        "foo partner 5",
        "foo partner 6",
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "foo partner 11",
        "foo partner 12",
        "Search More...",
    ]);

    // Open the search more dialog
    expect(`.modal`).toHaveCount(0);
    await contains(`${section} .o-autocomplete--dropdown-item:last-child`).click();
    expect(`.modal`).toHaveCount(1);
    expect(`.modal .o_data_row`).toHaveCount(10);
    expect(queryAllTexts`.modal .o_data_row`).toEqual([
        "foo partner 5",
        "foo partner 6",
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "foo partner 11",
        "foo partner 12",
        "foo partner 13",
        "foo partner 14",
    ]);
    await contains(".o_data_row:eq(0)").click();
    await contains(`.o-autocomplete--input`).edit("foo", { confirm: false });
    await advanceTime(500);
    await contains(`${section} .o-autocomplete--dropdown-item:last-child`).click();
    await contains(".o_data_row:eq(0)").click();
    expect("o_dialog").toHaveCount(0);

    expect(`.o_calendar_sidebar .o_calendar_filter`).toHaveCount(1);
    expect(`.o_calendar_filter_item`).toHaveCount(4);
    expect(queryAllTexts`.o_calendar_filter_item`).toEqual([
        "foo partner 5",
        "foo partner 6",
        "partner 1",
        "partner 2",
    ]);

    // Open the autocomplete dropdown
    expect(`${section} .o-autocomplete--dropdown-menu`).toHaveCount(0);
    expect(`${section} .o-autocomplete--dropdown-item`).toHaveCount(0);
    await contains(`${section} .o-autocomplete--input`).click();
    await advanceTime(500);
    expect(`${section} .o-autocomplete--dropdown-menu`).toHaveCount(1);
    expect(`${section} .o-autocomplete--dropdown-item`).toHaveCount(9);
    expect(queryAllTexts`.o-autocomplete--dropdown-item`).toEqual([
        "partner 3",
        "partner 4",
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "foo partner 11",
        "foo partner 12",
        "Search More...",
    ]);

    // Change the search term
    await contains(`.o-autocomplete--input`).edit("foo", { confirm: false });
    await advanceTime(500);
    expect(`${section} .o-autocomplete--dropdown-menu`).toHaveCount(1);
    expect(`${section} .o-autocomplete--dropdown-item`).toHaveCount(9);
    expect(queryAllTexts`.o-autocomplete--dropdown-item`).toEqual([
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "foo partner 11",
        "foo partner 12",
        "foo partner 13",
        "foo partner 14",
        "Search More...",
    ]);

    // Open the search more dialog
    expect(`.modal`).toHaveCount(0);
    await contains(`${section} .o-autocomplete--dropdown-item:last-child`).click();
    expect(`.modal`).toHaveCount(1);
    expect(`.modal .o_data_row`).toHaveCount(8);
    expect(queryAllTexts`.modal .o_data_row`).toEqual([
        "foo partner 7",
        "foo partner 8",
        "foo partner 9",
        "foo partner 10",
        "foo partner 11",
        "foo partner 12",
        "foo partner 13",
        "foo partner 14",
    ]);
    await closeCwPopOver();
    expect(`.modal`).toHaveCount(0);
    expect(`${section} .o_calendar_filter_item`).toHaveCount(4);
    expect(queryAllTexts`.o_calendar_filter_item`).toEqual([
        "foo partner 5",
        "foo partner 6",
        "partner 1",
        "partner 2",
    ]);
    expect(`.o-autocomplete--input`).toHaveValue("");
});

test(`delete attribute on calendar doesn't show delete button in popover`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="is_all_day" delete="0" mode="month"/>`,
    });

    await clickEvent(4);
    const container = getMockEnv().isSmall ? ".modal" : ".o_cw_popover";
    expect(container).toHaveCount(1);
    expect(`${container} .o_cw_popover_delete`).toHaveCount(0);
});

test.tags("desktop");
test(`create and change events on desktop`, async () => {
    onRpc("web_save", ({ args }) => {
        if (args[0].length) {
            expect.step("web_save");
            expect(args[1]).toEqual({ name: "event 4 modified" });
        }
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="is_all_day" mode="month"/>`,
    });
    expect(`.fc-dayGridMonth-view`).toHaveCount(1);

    // click on an existing event to open the formViewDialog
    await clickEvent(4);
    expect(`.o_cw_popover`).toHaveCount(1);
    expect(`.o_cw_popover .o_cw_popover_edit`).toHaveCount(1);
    expect(`.o_cw_popover .o_cw_popover_delete`).toHaveCount(1);
    expect(`.o_cw_popover .o_cw_popover_close`).toHaveCount(1);

    await contains(`.o_cw_popover .o_cw_popover_edit`).click();
    expect(`.modal-body`).toHaveCount(1);

    await contains(`.modal-body input`).edit("event 4 modified");
    await contains(`.modal-footer .o_form_button_save`).click();
    expect(`.modal-body`).toHaveCount(0);

    // create a new event, quick create only
    await clickDate("2016-12-13");
    expect(`.o-calendar-quick-create`).toHaveCount(1);

    await contains(`.o-calendar-quick-create--input`).edit("new event in quick create", {
        confirm: false,
    });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect(`.o_event[data-event-id="8"]`).toHaveText("new event in quick create");
    expect(
        `.fc-daygrid-event-harness:not(.fc-daygrid-event-harness-abs):contains("new event in quick create")`
    ).toHaveCount(1);

    // create a new event, quick create only (validated by pressing enter key)
    await clickDate("2016-12-13");
    expect(`.o-calendar-quick-create`).toHaveCount(1);

    await contains(`.o-calendar-quick-create--input`).edit(
        "new event in quick create validated by pressing enter key.",
        { confirm: "enter" }
    );
    expect(`.o_event[data-event-id="9"]`).toHaveText(
        "new event in quick create validated by pressing enter key."
    );

    // create a new event and edit it
    await clickDate("2016-12-27");
    expect(`.o-calendar-quick-create`).toHaveCount(1);

    await contains(`.o-calendar-quick-create--input`).edit("coucou", { confirm: false });
    await contains(`.o-calendar-quick-create--edit-btn`).click();
    expect(`.modal`).toHaveCount(1);
    expect(`.modal .modal-title`).toHaveText("New Event");
    expect(`.modal [name="name"] input`).toHaveValue("coucou");

    await contains(`.modal-footer .o_form_button_save`).click();
    expect(`.o_event[data-event-id="10"]`).toHaveText("coucou");

    // create a new event with 2 days
    await selectDateRange("2016-12-20", "2016-12-21");
    await contains(`.o-calendar-quick-create--input`).edit("new event in quick create 2", {
        confirm: false,
    });
    await contains(`.o-calendar-quick-create--edit-btn`).click();
    expect(`.modal .o_form_view [name="name"] input`).toHaveValue("new event in quick create 2");

    await contains(`.modal-footer .o_form_button_save`).click();
    expect(`.modal`).toHaveCount(0);

    expect(`.o_event[data-event-id="11"]`).toHaveText("new event in quick create 2");
    expectEventToBeOver(`.o_event[data-event-id="11"]`, [["2016-12-20", "2016-12-21"]]);

    await clickEvent(11);
    expect(`.o_cw_popover .list-group-item:eq(0)`).toHaveText("December 20-21, 2016 2 days");
    await closeCwPopOver();

    // delete the a record
    await clickEvent(4);
    await contains(`.o_cw_popover_delete`).click();
    expect(`.modal-title`).toHaveText("Bye-bye, record!");

    await contains(`.modal-footer button.btn-primary`).click();
    expect(`.o_event[data-event-id="4"]`).toHaveCount(0);
    expect(`.o_event`).toHaveCount(10);

    // move to next month
    await navigate("next");
    expect(`.o_event`).toHaveCount(0);

    await pickDate("2017-01-01");
    await changeScale("month");
    expect(`.o_event`).toHaveCount(0);

    await navigate("prev");
    await pickDate("2016-12-27");
    await changeScale("month");
    await selectDateRange("2016-12-20", "2016-12-21");
    await contains(`.o-calendar-quick-create--input`).edit("test", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect.verifySteps(["web_save"]);
});

test.tags("mobile");
test(`create and change events on mobile`, async () => {
    onRpc("web_save", ({ args }) => {
        if (args[0].length) {
            expect.step("web_save");
            expect(args[1]).toEqual({ name: "event 4 modified" });
        }
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="is_all_day" mode="month"/>`,
    });
    expect(`.fc-dayGridMonth-view`).toHaveCount(1);

    // click on an existing event to open the formViewDialog
    await clickEvent(4);
    const container = ".modal";
    const closeButton = ".oi-arrow-left";
    expect(container).toHaveCount(1);
    expect(`${container} .o_cw_popover_edit`).toHaveCount(1);
    expect(`${container} .o_cw_popover_delete`).toHaveCount(1);
    expect(`${container} ${closeButton}`).toHaveCount(1);

    await contains(`${container} .o_cw_popover_edit`).click();
    expect(`.modal-body`).toHaveCount(1);

    await contains(`.modal-body input:eq(0)`).edit("event 4 modified");
    await contains(`.modal-footer .o_form_button_save`).click();
    expect(`.modal-body`).toHaveCount(0);

    // create a new event, quick create only
    await clickDate("2016-12-13");
    expect(`.o-calendar-quick-create`).toHaveCount(1);

    await contains(`.o-calendar-quick-create--input`).edit("new event in quick create", {
        confirm: false,
    });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect(`.o_event[data-event-id="8"]`).toHaveText("new event in quick create");
    expect(
        `.fc-daygrid-event-harness:not(.fc-daygrid-event-harness-abs):contains("new event in quick create")`
    ).toHaveCount(1);

    // create a new event, quick create only (validated by pressing enter key)
    await clickDate("2016-12-13");
    expect(`.o-calendar-quick-create`).toHaveCount(1);

    await contains(`.o-calendar-quick-create--input`).edit(
        "new event in quick create validated by pressing enter key.",
        { confirm: "enter" }
    );
    expect(`.o_event[data-event-id="9"]`).toHaveText(
        "new event in quick create validated by pressing enter key."
    );

    // create a new event and edit it
    await clickDate("2016-12-27");
    expect(`.o-calendar-quick-create`).toHaveCount(1);

    await contains(`.o-calendar-quick-create--input`).edit("coucou", { confirm: false });
    await contains(`.o-calendar-quick-create--edit-btn`).click();
    expect(`.modal`).toHaveCount(1);
    expect(`.modal .modal-title`).toHaveText("New Event");
    expect(`.modal [name="name"] input`).toHaveValue("coucou");

    await contains(`.modal-footer .o_form_button_save`).click();
    expect(`.o_event[data-event-id="10"]`).toHaveText("coucou");

    // create a new event with 2 days
    await selectDateRange("2016-12-20", "2016-12-21");
    await contains(`.o-calendar-quick-create--input`).edit("new event in quick create 2", {
        confirm: false,
    });
    await contains(`.o-calendar-quick-create--edit-btn`).click();
    expect(`.modal .o_form_view [name="name"] input`).toHaveValue("new event in quick create 2");

    await contains(`.modal-footer .o_form_button_save`).click();
    expect(`.modal`).toHaveCount(0);

    expect(`.o_event[data-event-id="11"]`).toHaveText("new event in quick create 2");
    expectEventToBeOver(`.o_event[data-event-id="11"]`, [["2016-12-20", "2016-12-21"]]);

    await clickEvent(11);

    expect(`${container} .list-group-item:eq(0)`).toHaveText("December 20-21, 2016 2 days");

    await closeCwPopOver();

    // delete the a record
    await clickEvent(4);
    await contains(`.o_cw_popover_delete`).click();
    expect(`.modal-title`).toHaveText("Bye-bye, record!");

    await contains(`.modal-footer button.btn-primary`).click();
    expect(`.o_event[data-event-id="4"]`).toHaveCount(0);
    expect(`.o_event`).toHaveCount(10);

    // move to next month
    await navigate("next");

    expect(`.o_event`).toHaveCount(0);

    await navigate("prev");

    await selectDateRange("2016-12-20", "2016-12-21");
    await contains(`.o-calendar-quick-create--input`).edit("test", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();

    expect.verifySteps(["web_save"]);
});

test(`quickcreate with custom create_name_field`, async () => {
    class CustomEvent extends models.Model {
        _name = "custom.event";

        x_name = fields.Char();
        x_start_date = fields.Date();

        has_access() {
            return true;
        }

        _records = [{ id: 1, x_name: "some event", x_start_date: "2016-12-06" }];
    }
    defineModels([CustomEvent]);

    onRpc("create", ({ args }) => {
        expect.step("create");
        expect(args[0]).toEqual([
            {
                x_name: "custom event in quick create",
                x_start_date: "2016-12-13",
            },
        ]);
    });

    await mountView({
        resModel: "custom.event",
        type: "calendar",
        arch: `<calendar date_start="x_start_date" create_name_field="x_name" mode="month"/>`,
    });

    // create a new event
    await clickDate("2016-12-13");
    expect(`.o-calendar-quick-create`).toHaveCount(1);

    await contains(`.o-calendar-quick-create--input`).edit("custom event in quick create", {
        confirm: false,
    });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect(`.o_event[data-event-id="2"]`).toHaveCount(1);
    expect(`.o_event[data-event-id="2"]`).toHaveText("custom event in quick create");
    expect.verifySteps(["create"]);
});

test(`quickcreate switching to actual create for required fields`, async () => {
    onRpc("create", () => {
        throw makeServerError();
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="month" event_open_popup="1"/>`,
    });

    await clickDate("2016-12-13");
    expect(`.modal-title`).toHaveText("New Event");

    await contains(`.o-calendar-quick-create--input`).edit("custom event in quick create", {
        confirm: false,
    });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect(`.o-calendar-quick-create`).toHaveCount(0);
    expect(`.modal-title`).toHaveText("New Event");
    expect(`.modal .o_form_view .o_form_editable`).toHaveCount(1);
});

test(`open multiple event form at the same time`, async () => {
    let callCounter = 0;
    mockService("dialog", {
        add() {
            callCounter++;
            return super.add(...arguments);
        },
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="month" event_open_popup="1" quick_create="0">
                <field name="name"/>
            </calendar>
        `,
    });

    for (let i = 0; i < 5; i++) {
        await clickDate("2016-12-13");
    }

    expect(callCounter).toBe(5, { message: "there should had been 5 attemps to open a modal" });
    expect(`.modal`).toHaveCount(1, { message: "there should be only one open modal" });
});

test(`create event with timezone in week mode European locale`, async () => {
    mockTimeZone(2);
    Event._records = [];

    onRpc("create", ({ args }) => {
        expect.step("create");
        expect(args[0]).toEqual([
            {
                is_all_day: false,
                name: "new event",
                start: "2016-12-13 06:00:00",
                stop: "2016-12-13 08:00:00",
            },
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week" event_open_popup="1">
                <field name="name"/>
                <field name="start"/>
                <field name="is_all_day"/>
            </calendar>
        `,
    });
    await selectTimeRange("2016-12-13 08:00:00", "2016-12-13 10:00:00");
    expect(`.fc-event-main .fc-event-time`).toHaveText("08:00 - 10:00");

    await contains(`.o-calendar-quick-create--input`).edit("new event", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect.verifySteps(["create"]);
    expect(`.fc-event-main .o_event_title`).toHaveText("new event");

    await clickEvent(1);
    await contains(`.o_cw_popover_delete`).click();
    await contains(`.modal button.btn-primary`).click();
    expect(`.fc-event-main`).toHaveCount(0);
});

test(`create multi day event in week mode`, async () => {
    mockTimeZone(2);

    patchWithCleanup(CalendarCommonRenderer.prototype, {
        get options() {
            return { ...super.options, selectAllow: () => true };
        },
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="week"/>`,
    });
    await selectTimeRange("2016-12-13 11:00:00", "2016-12-14 16:00:00");
    expect(`.fc-event-main .fc-event-time`).toHaveText("11:00 - 16:00");
});

test(`default week start (US)`, async () => {
    // if not given any option, default week start is on Sunday
    mockTimeZone(-7);
    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2016-12-18 06:59:59"],
            ["stop", ">=", "2016-12-11 07:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="week"/>`,
    });
    expect.verifySteps(["event.search_read"]);
    expect(`.fc-col-header-cell .o_cw_day_name:eq(0)`).toHaveText("SUN");
    expect(`.fc-col-header-cell .o_cw_day_name:eq(-1)`).toHaveText("SAT");
});

test(`European week start`, async () => {
    // the week start depends on the locale
    defineParams({ lang_parameters: { week_start: 1 } });

    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2016-12-18 22:59:59"],
            ["stop", ">=", "2016-12-11 23:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="week"/>`,
    });
    expect.verifySteps(["event.search_read"]);
    expect(`.fc-col-header-cell .o_cw_day_name:eq(0)`).toHaveText("MON");
    expect(`.fc-col-header-cell .o_cw_day_name:eq(-1)`).toHaveText("SUN");
});

test.tags("desktop");
test(`week numbering`, async () => {
    // Using ISO week calculation, get the ISO week number of
    // the Monday nearest to the start of the week.
    defineParams({ lang_parameters: { week_start: 7 } });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="week"/>`,
    });
    expect(`.fc-timegrid-axis-cushion:eq(0)`).toHaveText("Week 50");
});

test.tags("desktop");
test(`render popover`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week">
                <field name="name" string="Custom Name"/>
                <field name="partner_id"/>
            </calendar>
        `,
    });

    await clickEvent(2);
    expect(`.o_cw_popover`).toHaveCount(1);
    expect(`.o_cw_popover .popover-header`).toHaveText("event 2");
    expect(`.o_cw_popover .o_cw_popover_edit`).toHaveCount(1);
    expect(`.o_cw_popover .o_cw_popover_delete`).toHaveCount(1);
    expect(`.o_cw_popover .o_cw_popover_close`).toHaveCount(1);
    expect(`.o_cw_popover .list-group-item:eq(0)`).toHaveText("December 12, 2016");
    expect(`.o_cw_popover .list-group-item:eq(1)`).toHaveText("11:55 - 15:55 (4 hours)");
    expect(`.o_cw_popover .o_cw_popover_fields_secondary .list-group-item`).toHaveCount(2);
    expect(
        `.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:eq(0) .o_field_char`
    ).toHaveCount(1);
    expect(
        `.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:eq(0) .o_field_char`
    ).toHaveText("event 2");
    expect(
        `.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:eq(0) span.fw-bold`
    ).toHaveText("Custom Name");
    expect(
        `.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:eq(1) .o_form_uri`
    ).toHaveCount(1);
    expect(
        `.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:eq(1) .o_form_uri`
    ).toHaveText("partner 1");
    expect(
        `.o_cw_popover .o_cw_popover_fields_secondary .list-group-item:eq(1) span.fw-bold`
    ).toHaveText("Partner");

    await contains(`.o_cw_popover .o_cw_popover_close`).click();
    expect(`.o_cw_popover`).toHaveCount(0);
});

test.tags("desktop");
test(`render popover with modifiers`, async () => {
    Event._fields.priority = fields.Selection({
        selection: [
            ["0", "Normal"],
            ["1", "Important"],
        ],
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week">
                <field name="priority" widget="priority" readonly="1"/>
                <field name="is_hatched" invisible="1"/>
                <field name="partner_id" invisible="not is_hatched"/>
                <field name="start" invisible="is_hatched"/>
            </calendar>
        `,
    });

    await clickEvent(4);
    expect(`.o_cw_popover`).toHaveCount(1);
    expect(`.o_cw_popover .o_priority span.o_priority_star`).toHaveCount(1);
    expect(`.o_cw_popover li.o_invisible_modifier`).toHaveCount(0);
    expect(`.o_cw_popover .o_field_datetime`).toHaveCount(1);

    await contains(`.o_cw_popover .o_cw_popover_close`).click();
    expect(`.o_cw_popover`).toHaveCount(0);
});

test.tags("desktop");
test(`render popover: inside fullcalendar popover`, async () => {
    // add 10 records the same day
    Event._records = Array.from({ length: 10 }).map((_, i) => ({
        id: i + 1,
        name: `event ${i + 1}`,
        start: "2016-12-14 10:00:00",
        stop: "2016-12-14 15:00:00",
        user_id: serverState.userId,
    }));

    mockService("action", {
        doAction(request) {
            expect.step("doAction");
            expect(request).toEqual({
                type: "ir.actions.act_window",
                res_model: "event",
                res_id: 1,
                views: [[false, "form"]],
                target: "current",
                context: {},
            });
            return super.doAction(request);
        },
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" mode="month">
                <field name="name" string="Custom Name"/>
                <field name="partner_id"/>
            </calendar>
        `,
    });

    expect(`:not(.fc-daygrid-event-harness-abs) > .fc-event`).toHaveCount(4);
    expect(`.fc-more-link`).toHaveCount(1);
    expect(`.fc-more-link`).toHaveText("+6 more");
    expect(`.fc-popover`).toHaveCount(0);

    await contains(`.fc-more-link`).click();
    expect(`.fc-popover`).toHaveCount(1);
    expect(`.fc-popover :not(.fc-daygrid-event-harness-abs) > .fc-event`).toHaveCount(10);
    expect(`.o_cw_popover`).toHaveCount(0);

    await contains(`.fc-popover .fc-daygrid-event-harness:nth-child(1) .fc-event`).click();
    await advanceTime(500);
    expect(`.o_cw_popover`).toHaveCount(1);

    await contains(`.o_cw_popover .o_cw_popover_edit`).click();
    expect.verifySteps(["doAction"]);
    expect(`.o_cw_popover`).toHaveCount(0);
    expect(`.fc-popover`).toHaveCount(1);
});

test(`attributes hide_date and hide_time`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" hide_date="1" hide_time="1" mode="month"/>`,
    });
    await clickEvent(4);
    expect(`.o_cw_popover .list-group-item`).toHaveCount(0);
});

test(`create event with timezone in week mode with formViewDialog`, async () => {
    mockTimeZone(2);

    Event._records = [];
    Event._onChanges.is_all_day = (record) => {
        if (record.is_all_day) {
            record.start_date = (record.start && record.start.split(" ")[0]) || record.start_date;
            record.stop_date =
                (record.stop && record.stop.split(" ")[0]) || record.stop_date || record.start_date;
        } else {
            record.start = (record.start_date && record.start_date + " 00:00:00") || record.start;
            record.stop =
                (record.stop_date && record.stop_date + " 00:00:00") || record.stop || record.start;
        }
    };

    onRpc("write", ({ args }) => expect.step(["write", args[1]]));
    onRpc("web_save", ({ kwargs }) => {
        expect.step("web_save");
        expect(kwargs.context).toEqual({
            default_name: "new event",
            default_start: "2016-12-13 06:00:00",
            default_stop: "2016-12-13 08:00:00",
            default_is_all_day: false,
            lang: "en",
            tz: "taht",
            uid: serverState.userId,
            allowed_company_ids: [1],
        });
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week" event_open_popup="1">
                <field name="name"/>
            </calendar>
        `,
    });

    await selectTimeRange("2016-12-13 08:00:00", "2016-12-13 10:00:00");
    await contains(`.o-calendar-quick-create--input`).edit("new event", { confirm: false });
    await contains(`.o-calendar-quick-create--edit-btn`).click();
    expect(`.o_field_widget[name='start']`).toHaveText("Dec 13, 8:00 AM");

    // Set is_all_day to true in formViewDialog
    await contains(`.modal .o_field_boolean[name='is_all_day'] input`).click();
    expect(`.o_field_widget[name='start_date']`).toHaveText("Dec 13");

    await contains(`.modal .o_field_boolean[name='is_all_day'] input`).click();
    expect(`.o_field_widget[name='start']`).toHaveText("Dec 13, 2:00 AM");

    // use datepicker to enter a date: 12/13/2016 08:00:00
    await contains(`.o_field_widget[name='start'] button`).click();
    await selectHourOnPicker("8");

    // use datepicker to enter a date: 12/13/2016 10:00:00
    await contains(`.o_field_widget[name='stop'] button`).click();
    await selectHourOnPicker("10");

    await contains(`.modal-footer .o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
    expect(`.o_event[data-event-id="1"] .o_event_title`).toHaveText("new event");

    // Move this event to another day
    await moveEventToTime(1, "2016-12-12 08:00:00");
    expect.verifySteps([
        ["write", { is_all_day: false, start: "2016-12-12 06:00:00", stop: "2016-12-12 08:00:00" }],
    ]);

    // Move to "All day"
    await moveEventToAllDaySlot(1, "2016-12-12");
    expect.verifySteps([["write", { is_all_day: true, start: "2016-12-12", stop: "2016-12-12" }]]);
});

test(`create event with timezone in week mode American locale`, async () => {
    mockTimeZone(2);
    Event._records = [];

    onRpc("create", ({ kwargs }) => {
        expect.step("create");
        expect(kwargs.context).toEqual({
            default_name: "new event",
            default_start: "2016-12-13 04:00:00",
            default_stop: "2016-12-13 06:00:00",
            default_is_all_day: false,
            lang: "en",
            tz: "taht",
            uid: serverState.userId,
            allowed_company_ids: [1],
        });
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" event_open_popup="1">
                <field name="name"/>
                <field name="start"/>
                <field name="is_all_day"/>
            </calendar>
        `,
    });

    await selectTimeRange("2016-12-13 06:00:00", "2016-12-13 08:00:00");
    await contains(`.o-calendar-quick-create--input`).edit("new event", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect(`.o_event[data-event-id="1"] .o_event_title`).toHaveText("new event");
    expect.verifySteps(["create"]);

    // delete record
    await clickEvent(1);
    await contains(`.o_cw_popover_delete`).click();
    await contains(`.modal button.btn-primary`).click();
    expect(`.fc-event-main`).toHaveCount(0);
});

test(`fetch event when being in timezone`, async () => {
    mockTimeZone(11);
    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2016-12-17 12:59:59"],
            ["stop", ">=", "2016-12-10 13:00:00"],
        ]);
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" mode="week">
                <field name="name"/>
                <field name="start"/>
                <field name="is_all_day"/>
            </calendar>
        `,
    });
    expect.verifySteps(["event.search_read"]);
    expect(`.fc-col-header-cell .o_cw_day_number:eq(0)`).toHaveText("11");
    expect(`.fc-col-header-cell .o_cw_day_number:eq(-1)`).toHaveText("17");
});

test(`check calendar week column time format`, async () => {
    defineParams({ lang_parameters: { time_format: "hh:mm:ss" } });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start"/>`,
    });
    expect(`.fc-timegrid-slot[data-time="08:00:00"]:eq(0)`).toHaveText("8am");
    expect(`.fc-timegrid-slot[data-time="23:00:00"]:eq(0)`).toHaveText("11pm");
});

test(`create all day event in week mode`, async () => {
    mockTimeZone(2);
    Event._records = [];

    onRpc("create", ({ args }) => {
        expect.step("create");
        expect(args[0]).toEqual([
            {
                name: "new event",
                start: "2016-12-14",
                stop: "2016-12-15",
                is_all_day: true,
            },
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week" event_open_popup="1">
                <field name="name"/>
            </calendar>
        `,
    });

    await selectAllDayRange("2016-12-14", "2016-12-15");
    await contains(`.o-calendar-quick-create--input`).edit("new event", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect(`.o_event[data-event-id="1"]`).toHaveText("new event");
    expect.verifySteps(["create"]);
    expectEventToBeOver(`.o_event[data-event-id="1"]`, [["2016-12-14", "2016-12-15"]]);
});

test(`create all day event in month mode: utc-11`, async () => {
    mockTimeZone(-11);
    Event._records = [];

    onRpc("create", ({ args }) => {
        expect.step("create");
        expect(args[0]).toEqual([
            {
                name: "new event",
                start: "2016-12-14",
                stop: "2016-12-14",
                is_all_day: true,
            },
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="month" event_open_popup="1">
                <field name="name"/>
            </calendar>
        `,
    });

    await clickDate("2016-12-14");
    await contains(`.o-calendar-quick-create--input`).edit("new event", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect.verifySteps(["create"]);
    expect(`.o_event[data-event-id="1"]`).toHaveText("new event");
    const eventRect = queryRect(`.o_event[data-event-id="1"]`);
    const cellRect = queryRect(`[data-date="2016-12-14"]`);
    expect(eventRect.left).toBeGreaterThan(cellRect.left);
    expect(eventRect.right).toBeLessThan(cellRect.right);
    expect(eventRect.top).toBeGreaterThan(cellRect.top);
    expect(eventRect.bottom).toBeLessThan(cellRect.bottom);
});

test.tags("desktop");
test(`create all day event in year mode: utc-11`, async () => {
    mockTimeZone(-11);
    Event._records = [];

    onRpc("create", ({ args }) => {
        expect.step("create");
        expect(args[0]).toEqual([
            {
                name: "new event",
                start: "2016-12-14",
                stop: "2016-12-14",
                is_all_day: true,
            },
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="year" event_open_popup="1">
                <field name="name"/>
            </calendar>
        `,
    });
    await clickDate("2016-12-14");
    await contains(`.o-calendar-quick-create--input`).edit("new event", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect.verifySteps(["create"]);
    expect(`.o_event[data-event-id="1"]`).toHaveRect(`[data-date="2016-12-14"]`);
});

test(`create event with default context (no quickCreate)`, async () => {
    mockTimeZone(2);
    Event._records = [];

    mockService("action", {
        doAction(request) {
            expect.step("doAction");
            expect(request.context).toEqual({
                default_name: "New",
                default_start: "2016-12-14",
                default_stop: "2016-12-15",
                default_is_all_day: true,
                lang: "en",
                tz: "taht",
                uid: serverState.userId,
                allowed_company_ids: [1],
            });
        },
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="week" all_day="is_all_day" quick_create="0"/>`,
        context: {
            default_name: "New",
        },
    });
    await selectAllDayRange("2016-12-14", "2016-12-15");
    expect.verifySteps(["doAction"]);
});

test(`create event with default title in context (with quickCreate)`, async () => {
    Event._records = [];

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="week" all_day="is_all_day"/>`,
        context: {
            default_name: "Example Title",
        },
    });
    await selectAllDayRange("2016-12-14", "2016-12-15");
    expect(`.o-calendar-quick-create--input`).toHaveValue("Example Title");
});

test(`create all day event in week mode (no quickCreate)`, async () => {
    mockTimeZone(2);
    Event._records = [];

    mockService("action", {
        doAction(request) {
            expect.step("doAction");
            expect(request.context).toEqual({
                default_start: "2016-12-14",
                default_stop: "2016-12-15",
                default_is_all_day: true,
                lang: "en",
                tz: "taht",
                uid: serverState.userId,
                allowed_company_ids: [1],
            });
        },
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week" quick_create="0"/>
        `,
    });
    await selectAllDayRange("2016-12-14", "2016-12-15");
    expect.verifySteps(["doAction"]);
});

test(`create event in month mode`, async () => {
    mockTimeZone(2);
    Event._records = [];

    onRpc("create", ({ args }) => {
        expect.step("create");
        expect(args[0]).toEqual([
            {
                name: "new event",
                start: "2016-12-14 05:00:00",
                stop: "2016-12-15 17:00:00",
            },
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" mode="month" event_open_popup="1">
                <field name="name"/>
            </calendar>
        `,
    });

    await selectDateRange("2016-12-14", "2016-12-15");
    await contains(`.o-calendar-quick-create--input`).edit("new event", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect(`.o_event[data-event-id="1"]`).toHaveText("new event");
    expect.verifySteps(["create"]);
    expectEventToBeOver(`.o_event[data-event-id="1"]`, [["2016-12-14", "2016-12-15"]]);
});

test.tags("desktop");
test(`use mini calendar`, async () => {
    mockTimeZone(2);

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week" event_open_popup="1"/>`,
    });
    expect(`.fc-timeGridWeek-view`).toHaveCount(1);
    expect(`.o_event`).toHaveCount(5);

    // Clicking on a day in another week should switch to the other week view
    await pickDate("2016-12-19");
    expect(`.fc-timeGridWeek-view`).toHaveCount(1);
    expect(`.o_event`).toHaveCount(2);

    // Clicking on a day in the same week should switch to that particular day view
    await pickDate("2016-12-18");
    expect(`.fc-timeGridDay-view`).toHaveCount(1);
    expect(`.o_event`).toHaveCount(2);

    // Clicking on the same day should toggle between day, month and week views
    await pickDate("2016-12-18");
    expect(`.fc-dayGridMonth-view`).toHaveCount(1);
    expect(`.o_event`).toHaveCount(7);

    await pickDate("2016-12-18");
    expect(`.fc-timeGridWeek-view`).toHaveCount(1);
    expect(`.o_event`).toHaveCount(2);

    await pickDate("2016-12-18");
    expect(`.fc-timeGridDay-view`).toHaveCount(1);
    expect(`.o_event`).toHaveCount(2);
});

test.tags("desktop");
test(`rendering, with many2many on desktop`, async () => {
    Event._fields.attendee_ids = fields.Many2many({
        relation: "calendar.partner",
        default: [[6, 0, [1]]],
    });
    Event._records[0].attendee_ids = [1, 2, 3, 4, 5];
    CalendarPartner._records.push({ id: 5, name: "partner 5", image: "EEE" });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" event_open_popup="1">
                <field name="attendee_ids" widget="many2many_tags_avatar" avatar_field="image" write_model="filter.partner" write_field="partner_id"/>
            </calendar>
        `,
    });
    expect(`.o_calendar_filter_item .o_cw_filter_avatar`).toHaveCount(2);

    await toggleSectionFilter("attendee_ids");
    await clickEvent(4);
    expect(`.o_cw_popover`).toHaveCount(1);
    expect(`.o_cw_popover img`).toHaveCount(1);

    await clickEvent(1);
    expect(`.o_cw_popover`).toHaveCount(1);
    expect(`.o_cw_popover img`).toHaveCount(5);
});

test.tags("mobile");
test(`rendering, with many2many on mobile`, async () => {
    Event._fields.attendee_ids = fields.Many2many({
        relation: "calendar.partner",
        default: [[6, 0, [1]]],
    });
    Event._records[0].attendee_ids = [1, 2, 3, 4, 5];
    CalendarPartner._records.push({ id: 5, name: "partner 5", image: "EEE" });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" event_open_popup="1">
                <field name="attendee_ids" widget="many2many_tags_avatar" avatar_field="image" write_model="filter.partner" write_field="partner_id"/>
            </calendar>
        `,
    });
    await displayCalendarPanel();
    expect(`.o_calendar_filter_item .o_cw_filter_avatar`).toHaveCount(2);
    await hideCalendarPanel();
    await toggleSectionFilter("attendee_ids");
    await clickEvent(4);
    expect(".modal").toHaveCount(1);
    expect(`.modal img`).toHaveCount(1);
    await closeCwPopOver();
    await clickEvent(1);
    expect(".modal").toHaveCount(1);
    expect(`.modal img`).toHaveCount(5);
});

test.tags("desktop");
test(`set filter with many2many field on desktop`, async () => {
    Event._fields.attendee_ids = fields.Many2many({
        relation: "calendar.partner",
        default: [[6, 0, [1]]],
    });
    Event._records[0].attendee_ids = [1, 2, 3, 4, 5];
    CalendarPartner._records.push({ id: 5, name: "partner 5", image: "EEE" });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" event_open_popup="1">
                <field name="attendee_ids" filters="1"/>
            </calendar>
        `,
    });
    expect(`.o_calendar_filter_item`).toHaveCount(5);
    expect(`.o_event[data-event-id="1"] .fc-event-main`).toHaveCount(1);
    expect(`.o_event[data-event-id="5"] .fc-event-main`).toHaveCount(1);

    await toggleSectionFilter("attendee_ids");
    expect(`.o_event[data-event-id="1"] .fc-event-main`).toHaveCount(0);
    expect(`.o_event[data-event-id="5"] .fc-event-main`).toHaveCount(0);

    await toggleFilter("attendee_ids", "1");
    expect(`.o_event[data-event-id="1"] .fc-event-main`).toHaveCount(1);
    expect(`.o_event[data-event-id="5"] .fc-event-main`).toHaveCount(0);
});

test.tags("mobile");
test(`set filter with many2many field on mobile`, async () => {
    Event._fields.attendee_ids = fields.Many2many({
        relation: "calendar.partner",
        default: [[6, 0, [1]]],
    });
    Event._records[0].attendee_ids = [1, 2, 3, 4, 5];
    CalendarPartner._records.push({ id: 5, name: "partner 5", image: "EEE" });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" event_open_popup="1">
                <field name="attendee_ids" filters="1"/>
            </calendar>
        `,
    });
    await contains(`.o_filter`).click();
    expect(`.o_calendar_filter_item`).toHaveCount(5);
    await contains(`.o_filter`).click();
    expect(`.o_event[data-event-id="1"] .fc-event-main`).toHaveCount(1);
    expect(`.o_event[data-event-id="5"] .fc-event-main`).toHaveCount(1);

    await toggleSectionFilter("attendee_ids");
    expect(`.o_event[data-event-id="1"] .fc-event-main`).toHaveCount(0);
    expect(`.o_event[data-event-id="5"] .fc-event-main`).toHaveCount(0);

    await toggleFilter("attendee_ids", "1");
    expect(`.o_event[data-event-id="1"] .fc-event-main`).toHaveCount(1);
    expect(`.o_event[data-event-id="5"] .fc-event-main`).toHaveCount(0);
});

test.tags("desktop");
test(`set filter with one2many field on desktop`, async () => {
    Event._fields.attendee_ids = fields.One2many({
        relation: "calendar.partner",
        default: [[6, 0, [1]]],
    });
    Event._records[0].attendee_ids = [1, 2, 3, 4, 5];
    CalendarPartner._records.push({ id: 5, name: "partner 5", image: "EEE" });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" event_open_popup="1">
                <field name="attendee_ids" filters="1"/>
            </calendar>
        `,
    });
    expect(`.o_calendar_filter_item`).toHaveCount(5);
    expect(`.o_event[data-event-id="1"] .fc-event-main`).toHaveCount(1);
    expect(`.o_event[data-event-id="5"] .fc-event-main`).toHaveCount(1);

    await toggleSectionFilter("attendee_ids");
    expect(`.o_event[data-event-id="1"] .fc-event-main`).toHaveCount(0);
    expect(`.o_event[data-event-id="5"] .fc-event-main`).toHaveCount(0);

    await toggleFilter("attendee_ids", "1");
    expect(`.o_event[data-event-id="1"] .fc-event-main`).toHaveCount(1);
    expect(`.o_event[data-event-id="5"] .fc-event-main`).toHaveCount(0);
});

test.tags("mobile");
test(`set filter with one2many field on mobile`, async () => {
    Event._fields.attendee_ids = fields.One2many({
        relation: "calendar.partner",
        default: [[6, 0, [1]]],
    });
    Event._records[0].attendee_ids = [1, 2, 3, 4, 5];
    CalendarPartner._records.push({ id: 5, name: "partner 5", image: "EEE" });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" event_open_popup="1">
                <field name="attendee_ids" filters="1"/>
            </calendar>
        `,
    });
    await contains(`.o_filter`).click();
    expect(`.o_calendar_filter_item`).toHaveCount(5);
    await contains(`.o_filter`).click();
    expect(`.o_event[data-event-id="1"] .fc-event-main`).toHaveCount(1);
    expect(`.o_event[data-event-id="5"] .fc-event-main`).toHaveCount(1);

    await toggleSectionFilter("attendee_ids");
    expect(`.o_event[data-event-id="1"] .fc-event-main`).toHaveCount(0);
    expect(`.o_event[data-event-id="5"] .fc-event-main`).toHaveCount(0);

    await toggleFilter("attendee_ids", "1");
    expect(`.o_event[data-event-id="1"] .fc-event-main`).toHaveCount(1);
    expect(`.o_event[data-event-id="5"] .fc-event-main`).toHaveCount(0);
});

test(`open form view`, async () => {
    let expectedRequest;
    mockService("action", {
        doAction(request) {
            expect.step("doAction");
            expect(request).toEqual(expectedRequest);
            return super.doAction(request);
        },
    });

    onRpc("get_formview_id", () => expect.step("get_formview_id")); // should not be called
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="month"/>`,
    });

    expectedRequest = {
        type: "ir.actions.act_window",
        res_id: 4,
        res_model: "event",
        views: [[false, "form"]],
        target: "current",
        context: {},
    };
    await clickEvent(4);
    await contains(`.o_cw_popover_edit`).click();
    expect.verifySteps(["doAction"]);

    await clickDate("2016-12-27");
    await contains(`.o-calendar-quick-create--input`).edit("coucou", { confirm: false });
    expectedRequest = {
        type: "ir.actions.act_window",
        res_model: "event",
        views: [[false, "form"]],
        target: "current",
        context: {
            default_name: "coucou",
            default_start: "2016-12-27",
            default_stop: "2016-12-27",
            default_is_all_day: true,
            lang: "en",
            tz: "taht",
            uid: serverState.userId,
            allowed_company_ids: [1],
        },
    };
    await contains(`.o-calendar-quick-create--edit-btn`).click();
    expect.verifySteps(["doAction"]);
});

test(`create and edit event in month mode (all_day: false)`, async () => {
    mockTimeZone(-4);

    mockService("action", {
        doAction(request) {
            expect.step("doAction");
            expect(request).toEqual({
                type: "ir.actions.act_window",
                res_model: "event",
                views: [[false, "form"]],
                target: "current",
                context: {
                    default_name: "coucou",
                    default_start: "2016-12-27 11:00:00", // 7:00 + 4h
                    default_stop: "2016-12-27 23:00:00", // 19:00 + 4h
                    default_allday: true,
                    lang: "en",
                    tz: "taht",
                    uid: serverState.userId,
                    allowed_company_ids: [1],
                },
            });
        },
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="month"/>`,
    });

    await clickDate("2016-12-27");
    await contains(`.o-calendar-quick-create--input`).edit("coucou", { confirm: false });
    await contains(`.o-calendar-quick-create--edit-btn`).click();
    expect.verifySteps(["doAction"]);
});

test(`show start time of single day event`, async () => {
    mockTimeZone(-4);

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="month"/>`,
    });
    expect(`.o_event[data-event-id="2"] .fc-event-main .fc-time`).toHaveText("06:55");
    expect(`.o_event[data-event-id="4"] .fc-event-main .fc-time`).toHaveCount(0);
    expect(`.o_event[data-event-id="5"] .fc-event-main .fc-time`).toHaveCount(0);

    await changeScale("week");
    expect(`.o_event[data-event-id="2"] .fc-event-main .fc-time`).toHaveCount(1);
});

test(`start time should not shown for date type field`, async () => {
    mockTimeZone(-4);

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start_date" date_stop="stop_date" mode="month"/>`,
    });
    expect(`.o_event[data-event-id="2"] .fc-event-main .fc-time`).toHaveCount(0);

    await changeScale("week");
    expect(`.o_event[data-event-id="2"] .fc-event-main .fc-time`).toHaveCount(0);

    await changeScale("day");
    expect(`.o_event[data-event-id="2"] .fc-event-main .fc-time`).toHaveCount(0);
});

test(`start time should not shown if hide_time is true`, async () => {
    mockTimeZone(-4);

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="month" hide_time="1"/>`,
    });
    expect(`.o_event[data-event-id="2"] .fc-event-main .fc-time`).toHaveCount(0);

    await changeScale("week");
    expect(`.o_event[data-event-id="2"] .fc-event-main .fc-time`).toHaveCount(0);

    await changeScale("day");
    expect(`.o_event[data-event-id="2"] .fc-event-main .fc-time`).toHaveCount(0);
});

test(`readonly date_start field`, async () => {
    Event._fields.start = fields.Datetime({ readonly: true });

    let expectedRequest;
    mockService("action", {
        doAction(request) {
            expect.step("doAction");
            expect(request).toEqual(expectedRequest);
        },
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="month"/>`,
    });
    expect(`.fc-resizer`).toHaveCount(0);

    expectedRequest = {
        type: "ir.actions.act_window",
        res_id: 4,
        res_model: "event",
        views: [[false, "form"]],
        target: "current",
        context: {},
    };
    await clickEvent(4);
    await contains(`.o_cw_popover_edit`).click();
    expect.verifySteps(["doAction"]);

    // create a new event and edit it
    await clickDate("2016-12-27");
    await contains(`.o-calendar-quick-create--input`).edit("coucou", { confirm: false });
    expectedRequest = {
        type: "ir.actions.act_window",
        res_model: "event",
        views: [[false, "form"]],
        target: "current",
        context: {
            allowed_company_ids: [1],
            default_name: "coucou",
            default_start: "2016-12-27",
            default_stop: "2016-12-27",
            default_is_all_day: true,
            lang: "en",
            tz: "taht",
            uid: serverState.userId,
        },
    };
    await contains(`.o-calendar-quick-create--edit-btn`).click();
    expect.verifySteps(["doAction"]);
});

test(`readonly calendar view`, async () => {
    let expectedRequest;
    mockService("action", {
        doAction(request) {
            expect.step("doAction");
            expect(request).toEqual(expectedRequest);
        },
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="month" edit="0"/>`,
    });
    expect(`.fc-resizer`).toHaveCount(0);

    expectedRequest = {
        type: "ir.actions.act_window",
        res_id: 4,
        res_model: "event",
        views: [[false, "form"]],
        target: "current",
        context: {},
    };
    await clickEvent(4);
    await contains(`.o_cw_popover_edit`).click();
    expect.verifySteps(["doAction"]);

    // create a new event and edit it
    await clickDate("2016-12-27");
    await contains(`.o-calendar-quick-create--input`).edit("coucou", { confirm: false });
    expectedRequest = {
        type: "ir.actions.act_window",
        res_model: "event",
        views: [[false, "form"]],
        target: "current",
        context: {
            allowed_company_ids: [1],
            default_name: "coucou",
            default_start: "2016-12-27",
            default_stop: "2016-12-27",
            default_is_all_day: true,
            lang: "en",
            tz: "taht",
            uid: serverState.userId,
        },
    };
    await contains(`.o-calendar-quick-create--edit-btn`).click();
    expect.verifySteps(["doAction"]);
});

test.tags("desktop");
test(`check filters with filter_field specified on desktop`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id" filter_field="is_checked"/>
            </calendar>
        `,
    });
    expect(
        `.o_calendar_filter[data-name="attendee_ids"] .o_calendar_filter_item[data-value="2"] input:checked`
    ).toHaveCount(1);
    expect(MockServer.env["filter.partner"].read([2])[0].is_checked).toBe(true);

    await toggleFilter("attendee_ids", 2);
    expect(
        `.o_calendar_filter[data-name="attendee_ids"] .o_calendar_filter_item[data-value="2"] input:checked`
    ).toHaveCount(0);
    expect(MockServer.env["filter.partner"].read([2])[0].is_checked).toBe(false);

    await changeScale("week"); // trick to reload the entire view
    expect(
        `.o_calendar_filter[data-name="attendee_ids"] .o_calendar_filter_item[data-value="2"] input:checked`
    ).toHaveCount(0);
    expect(MockServer.env["filter.partner"].read([2])[0].is_checked).toBe(false);
});

test.tags("mobile");
test(`check filters with filter_field specified on mobile`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id" filter_field="is_checked"/>
            </calendar>
        `,
    });
    await displayCalendarPanel();
    expect(
        `.o_calendar_filter[data-name="attendee_ids"] .o_calendar_filter_item[data-value="2"] input:checked`
    ).toHaveCount(1);
    expect(MockServer.env["filter.partner"].read([2])[0].is_checked).toBe(true);
    await hideCalendarPanel();
    await toggleFilter("attendee_ids", 2);
    await displayCalendarPanel();
    expect(
        `.o_calendar_filter[data-name="attendee_ids"] .o_calendar_filter_item[data-value="2"] input:checked`
    ).toHaveCount(0);
    expect(MockServer.env["filter.partner"].read([2])[0].is_checked).toBe(false);
    await hideCalendarPanel();
    await changeScale("week"); // trick to reload the entire view
    await displayCalendarPanel();
    expect(
        `.o_calendar_filter[data-name="attendee_ids"] .o_calendar_filter_item[data-value="2"] input:checked`
    ).toHaveCount(0);
    expect(MockServer.env["filter.partner"].read([2])[0].is_checked).toBe(false);
});

test(`dynamic filters with selection fields`, async () => {
    Event._fields.selection = fields.Selection({
        string: "Ambiance",
        selection: [
            ["desert", "Desert"],
            ["forest", "Forest"],
        ],
    });

    Event._records[0].selection = "forest";
    Event._records[1].selection = "desert";

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop">
                <field name="selection" filters="1"/>
            </calendar>
        `,
    });
    await displayCalendarPanel();
    expect(`.o_calendar_filter[data-name="selection"] .o_cw_filter_label`).toHaveText("Ambiance");
    expect(
        queryAllTexts(`.o_calendar_filter[data-name="selection"] .o_calendar_filter_item`)
    ).toEqual(["Desert", "Forest", "Undefined"]);
});

test(`Colors: cycling through available colors`, async () => {
    FilterPartner._records = Array.from({ length: 56 }, (_, i) => ({
        id: i + 1,
        user_id: serverState.userId,
        partner_id: i + 1,
        is_checked: true,
    }));
    CalendarPartner._records = Array.from({ length: 56 }, (_, i) => ({
        id: i + 1,
        name: `partner ${i + 1}`,
    }));
    Event._records = Array.from({ length: 56 }, (_, i) => ({
        id: i + 1,
        user_id: serverState.userId,
        partner_id: i + 1,
        name: `event ${i + 1}`,
        start: `2016-12-12 0${i % 10}:00:00`,
        stop: `2016-12-12 0${i % 10}:00:00`,
        attendee_ids: [i + 1],
    }));
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" mode="day" color="attendee_ids">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id" filter_field="is_checked" />
            </calendar>
        `,
    });
    expect(`.o_event`).toHaveCount(56);
    expect(`.o_event[data-event-id="1"]`).toHaveClass("o_calendar_color_1");
    expect(`.o_event[data-event-id="55"]`).toHaveClass("o_calendar_color_55");
    expect(`.o_event[data-event-id="56"]`).toHaveClass("o_calendar_color_1");
    await displayCalendarPanel();
    expect(
        `.o_calendar_filter[data-name="attendee_ids"] .o_calendar_filter_item[data-value="1"]`
    ).toHaveClass("o_cw_filter_color_1");
    expect(
        `.o_calendar_filter[data-name="attendee_ids"] .o_calendar_filter_item[data-value="55"]`
    ).toHaveClass("o_cw_filter_color_55");
    expect(
        `.o_calendar_filter[data-name="attendee_ids"] .o_calendar_filter_item[data-value="56"]`
    ).toHaveClass("o_cw_filter_color_1");
});

test.tags("desktop");
test(`Colors: use available colors when attr is not number on desktop`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" color="name">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id" filter_field="is_checked" />
            </calendar>
        `,
    });
    const colorClass = Array.from(queryFirst`.o_event[data-event-id="1"]`.classList).find(
        (className) => className.startsWith("o_calendar_color_")
    );
    expect(isNaN(Number(colorClass.split("_").at(-1)))).toBe(false);

    await clickEvent(1);
    expect(`.o_cw_popover`).toHaveClass(colorClass);
});

test.tags("mobile");
test(`Colors: use available colors when attr is not number on mobile`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" color="name">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id" filter_field="is_checked" />
            </calendar>
        `,
    });
    const colorClass = Array.from(queryFirst`.o_event[data-event-id="1"]`.classList).find(
        (className) => className.startsWith("o_calendar_color_")
    );
    expect(isNaN(Number(colorClass.split("_").at(-1)))).toBe(false);
});

test(`Add filters and specific color`, async () => {
    EventType._records.push({
        id: 4,
        name: "Event Type no color",
        color: 0,
    });
    Event._records.push(
        {
            id: 8,
            user_id: 4,
            partner_id: 1,
            name: "event 8",
            start: "2016-12-11 09:00:00",
            stop: "2016-12-11 10:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 3,
        },
        {
            id: 9,
            user_id: 4,
            partner_id: 1,
            name: "event 9",
            start: "2016-12-11 19:00:00",
            stop: "2016-12-11 20:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 1,
        },
        {
            id: 10,
            user_id: 4,
            partner_id: 1,
            name: "event 10",
            start: "2016-12-11 12:00:00",
            stop: "2016-12-11 13:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 4,
        }
    );

    onRpc(({ model, method, kwargs }) => {
        let step = `${method} (${model})`;
        if (kwargs.fields) {
            step += ` [${kwargs.fields.join(", ")}]`;
        }
        expect.step(step);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week" color="color" event_open_popup="1">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="type_id" filters="1" color="color"/>
            </calendar>
        `,
    });
    expect.verifySteps([
        "get_views (event)",
        "search_read (filter.partner) [partner_id]",
        "search_read (event) [display_name, start, stop, is_all_day, color, attendee_ids, type_id]",
    ]);

    // By default no filter is selected. We check before continuing.
    await toggleFilter("attendee_ids", 1);
    expect.verifySteps([
        "search_read (filter.partner) [partner_id]",
        "search_read (event) [display_name, start, stop, is_all_day, color, attendee_ids, type_id]",
    ]);

    await toggleFilter("attendee_ids", 2);
    expect.verifySteps([
        "search_read (filter.partner) [partner_id]",
        "search_read (event) [display_name, start, stop, is_all_day, color, attendee_ids, type_id]",
    ]);

    expect(`.o_event[data-event-id="8"]`).toHaveClass("o_calendar_color_4");
    expect(`.o_event[data-event-id="9"]`).toHaveClass("o_calendar_color_1");
    expect(`.o_event[data-event-id="10"]`).toHaveClass("o_calendar_color_0");

    await displayCalendarPanel();
    expect(`.o_calendar_filter`).toHaveCount(2);
    expect(`.o_calendar_filter[data-name="type_id"] .o_cw_filter_label`).toHaveText("Event Type");
    expect(`.o_calendar_filter[data-name="type_id"] .o_calendar_filter_item`).toHaveCount(4);
    expect(
        `.o_calendar_filter[data-name="type_id"] .o_calendar_filter_item[data-value="3"]`
    ).toHaveClass("o_cw_filter_color_4");
});

test(`Colors: dynamic filters without any color attr`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop">
                <field name="user_id" filters="1" invisible="1"/>
            </calendar>
        `,
    });
    expect(`.o_event[data-event-id="1"]`).toHaveClass("o_calendar_color_0");
    expect(`.o_event[data-event-id="2"]`).toHaveClass("o_calendar_color_0");
    expect(`.o_event[data-event-id="3"]`).toHaveClass("o_calendar_color_0");
    expect(`.o_event[data-event-id="4"]`).toHaveClass("o_calendar_color_0");
    await displayCalendarPanel();
    expect(`.o_calendar_filter[data-name="user_id"]`).toHaveCount(1);
    expect(`.o_calendar_filter[data-name="user_id"] [class*='o_cw_filter_color_']`).toHaveCount(0);
});

test(`Colors: dynamic filters without color attr (related)`, async () => {
    Event._records = [
        {
            id: 8,
            user_id: 4,
            partner_id: 1,
            name: "event 8",
            start: "2016-12-11 09:00:00",
            stop: "2016-12-11 10:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 3,
        },
        {
            id: 9,
            user_id: 4,
            partner_id: 1,
            name: "event 9",
            start: "2016-12-11 19:00:00",
            stop: "2016-12-11 20:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 1,
        },
        {
            id: 10,
            user_id: 4,
            partner_id: 1,
            name: "event 10",
            start: "2016-12-11 12:00:00",
            stop: "2016-12-11 13:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 2,
        },
    ];

    onRpc("event.type", "search_read", () => {
        throw makeServerError({ message: "should not fetch event.type filter colors" });
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" color="color">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="type_id" filters="1"/>
            </calendar>
        `,
    });
    await toggleSectionFilter("attendee_ids");
    expect(`.o_event[data-event-id="8"]`).toHaveClass("o_calendar_color_4");
    expect(`.o_event[data-event-id="9"]`).toHaveClass("o_calendar_color_1");
    expect(`.o_event[data-event-id="10"]`).toHaveClass("o_calendar_color_2");
    await displayCalendarPanel();
    expect(
        `.o_calendar_filter[data-name="attendee_ids"] [class*='o_cw_filter_color_']`
    ).toHaveCount(0);
    expect(`.o_calendar_filter[data-name="type_id"] [class*='o_cw_filter_color_']`).toHaveCount(3);
});

test(`Colors: dynamic filters without color attr (direct)`, async () => {
    onRpc("event.type", "search_read", () => {
        throw makeServerError({ message: "should not fetch event.type filter colors" });
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" color="user_id">
                <field name="partner_id" avatar_field="image"/>
                <field name="user_id" filters="1" invisible="1"/>
            </calendar>
        `,
    });
    expect(`.o_event[data-event-id="1"]`).toHaveClass("o_calendar_color_7"); // uid = serverState.user_id
    expect(`.o_event[data-event-id="2"]`).toHaveClass("o_calendar_color_7"); // uid = serverState.user_id
    expect(`.o_event[data-event-id="3"]`).toHaveClass("o_calendar_color_4");
    expect(`.o_event[data-event-id="4"]`).toHaveClass("o_calendar_color_7"); // uid = serverState.user_id
    await displayCalendarPanel();
    expect(`.o_calendar_filter[data-name="partner_id"] [class*='o_cw_filter_color_']`).toHaveCount(
        0
    );
    expect(`.o_calendar_filter[data-name="user_id"] [class*='o_cw_filter_color_']`).toHaveCount(2);
});

test(`makeFilterUser: color for current user`, async () => {
    class ResPartner extends models.Model {
        _name = "res.partner";

        name = fields.Char();
        image = fields.Char();

        _records = [
            { id: 1, name: "partner 1", image: "AAA" },
            { id: 2, name: "partner 2", image: "BBB" },
            { id: 3, name: "partner 3", image: "CCC" },
            { id: 4, name: "partner 4", image: "DDD" },
        ];
    }
    defineModels([ResPartner]);

    Event._fields.partner_id = fields.Many2one({ relation: "res.partner", default: 1 });
    Event._fields.attendee_ids = fields.One2many({
        relation: "res.partner",
        default: [[6, 0, [1]]],
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" color="attendee_ids">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
            </calendar>
        `,
    });

    await displayCalendarPanel();
    const section = `.o_calendar_filter[data-name="attendee_ids"]`;
    expect(`${section} [class*='o_cw_filter_color_']`).toHaveCount(3);
    expect(`${section} .o_cw_filter_label`).toHaveText("Attendees");
    expect(`${section} .o_calendar_filter_item`).toHaveCount(3);
    expect(`${section} .o_calendar_filter_item[data-value="17"]`).toHaveText("Mitchell Admin");
    expect(`${section} .o_calendar_filter_item[data-value="17"]`).toHaveClass(
        "o_cw_filter_color_17"
    );
    expect(`${section} .o_calendar_filter_item[data-value="2"]`).toHaveClass("o_cw_filter_color_2");
    expect(`${section} .o_calendar_filter_item[data-value="1"]`).toHaveClass("o_cw_filter_color_1");
});

test(`Colors: dynamic filters with same color as events`, async () => {
    Event._records = [
        {
            id: 8,
            user_id: 4,
            partner_id: 1,
            name: "event 8",
            start: "2016-12-11 09:00:00",
            stop: "2016-12-11 10:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 3,
        },
        {
            id: 9,
            user_id: 4,
            partner_id: 1,
            name: "event 9",
            start: "2016-12-11 19:00:00",
            stop: "2016-12-11 20:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 1,
        },
        {
            id: 10,
            user_id: 4,
            partner_id: 1,
            name: "event 10",
            start: "2016-12-11 12:00:00",
            stop: "2016-12-11 13:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 2,
        },
    ];

    onRpc("event.type", "search_read", () => {
        throw makeServerError({ message: "should not fetch event.type filter colors" });
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" color="color">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="type_id" filters="1" color="color"/>
            </calendar>
        `,
    });
    await toggleSectionFilter("attendee_ids");
    expect(`.o_event[data-event-id="8"]`).toHaveClass("o_calendar_color_4");
    expect(`.o_event[data-event-id="9"]`).toHaveClass("o_calendar_color_1");
    expect(`.o_event[data-event-id="10"]`).toHaveClass("o_calendar_color_2");
    await displayCalendarPanel();
    expect(`.o_calendar_filter[data-name="type_id"] [class*='o_cw_filter_color_']`).toHaveCount(3);
    expect(
        `.o_calendar_filter[data-name="type_id"] .o_calendar_filter_item[data-value="1"]`
    ).toHaveClass("o_cw_filter_color_1");
    expect(
        `.o_calendar_filter[data-name="type_id"] .o_calendar_filter_item[data-value="2"]`
    ).toHaveClass("o_cw_filter_color_2");
    expect(
        `.o_calendar_filter[data-name="type_id"] .o_calendar_filter_item[data-value="3"]`
    ).toHaveClass("o_cw_filter_color_4");
});

test(`Colors: dynamic filters with another color source`, async () => {
    Event._records = [
        {
            id: 8,
            user_id: 4,
            name: "event 8",
            start: "2016-12-11 09:00:00",
            stop: "2016-12-11 10:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 3,
        },
        {
            id: 9,
            user_id: 4,
            name: "event 9",
            start: "2016-12-11 19:00:00",
            stop: "2016-12-11 20:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 1,
        },
        {
            id: 10,
            user_id: 4,
            name: "event 10",
            start: "2016-12-11 12:00:00",
            stop: "2016-12-11 13:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 2,
        },
    ];

    onRpc("event.type", "search_read", () => {
        expect.step("fetching event.type filter colors");
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" color="partner_id">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="type_id" filters="1" color="color"/>
            </calendar>
        `,
    });
    expect.verifySteps([]);

    await toggleSectionFilter("attendee_ids");
    expect.verifySteps(["fetching event.type filter colors"]);
    expect(`.o_event[data-event-id="8"]`).toHaveClass("o_calendar_color_4");
    expect(`.o_event[data-event-id="9"]`).toHaveClass("o_calendar_color_4");
    expect(`.o_event[data-event-id="10"]`).toHaveClass("o_calendar_color_4");
    await displayCalendarPanel();
    expect(
        `.o_calendar_filter[data-name="type_id"] .o_calendar_filter_item[data-value="1"]`
    ).toHaveClass("o_cw_filter_color_1");
    expect(
        `.o_calendar_filter[data-name="type_id"] .o_calendar_filter_item[data-value="2"]`
    ).toHaveClass("o_cw_filter_color_2");
    expect(
        `.o_calendar_filter[data-name="type_id"] .o_calendar_filter_item[data-value="3"]`
    ).toHaveClass("o_cw_filter_color_4");
});

test(`Colors: dynamic filters with no color source`, async () => {
    Event._records = [
        {
            id: 8,
            user_id: 4,
            name: "event 8",
            start: "2016-12-11 09:00:00",
            stop: "2016-12-11 10:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 3,
        },
        {
            id: 9,
            user_id: 4,
            name: "event 9",
            start: "2016-12-11 19:00:00",
            stop: "2016-12-11 20:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 1,
        },
        {
            id: 10,
            user_id: 4,
            name: "event 10",
            start: "2016-12-11 12:00:00",
            stop: "2016-12-11 13:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
            type_id: 2,
        },
    ];

    onRpc("event.type", "search_read", () => {
        expect.step("fetching event.type filter colors");
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="type_id" filters="1" color="color"/>
            </calendar>
        `,
    });
    expect.verifySteps([]);

    await toggleSectionFilter("attendee_ids");
    expect.verifySteps(["fetching event.type filter colors"]);
    await displayCalendarPanel();
    expect(
        `.o_calendar_filter[data-name="type_id"] .o_calendar_filter_item[data-value="1"]`
    ).toHaveClass("o_cw_filter_color_1");
    expect(
        `.o_calendar_filter[data-name="type_id"] .o_calendar_filter_item[data-value="2"]`
    ).toHaveClass("o_cw_filter_color_2");
    expect(
        `.o_calendar_filter[data-name="type_id"] .o_calendar_filter_item[data-value="3"]`
    ).toHaveClass("o_cw_filter_color_4");
});

test(`create event with filters`, async () => {
    Event._fields.user_id = fields.Many2one({ relation: "calendar.users", default: 5 });
    Event._fields.partner_id = fields.Many2one({ relation: "calendar.partner", default: 3 });
    CalendarUsers._records.push({ id: 5, name: "user 5", partner_id: 3 });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week" event_open_popup="1" attendee="attendee_ids" color="partner_id">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="partner_id" filters="1" invisible="1"/>
            </calendar>
        `,
    });

    // By default only
    await toggleFilter("attendee_ids", 1);
    await checkFilterItems(4);
    expect(`.o_event`).toHaveCount(4);

    // quick create a record
    await selectTimeRange("2016-12-15 06:00:00", "2016-12-15 08:00:00");
    await contains(`.o-calendar-quick-create--input`).edit("coucou", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    await checkFilterItems(5);
    expect(`.o_event`).toHaveCount(5);

    // change default value for quick create an hide record
    Event._fields.user_id.default = 4;
    Event._fields.partner_id.default = 4;

    // Disable our filter to create a record without displaying it
    await toggleFilter("partner_id", 4);

    // quick create and other record
    await selectTimeRange("2016-12-13 06:00:00", "2016-12-13 08:00:00");
    await contains(`.o-calendar-quick-create--input`).edit("coucou 2", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    await checkFilterItems(5);
    expect(`.o_event`).toHaveCount(4);

    await toggleFilter("partner_id", 4);
    await toggleFilter("attendee_ids", 2);
    expect(`.o_event`).toHaveCount(7);
});

test(`create event with filters (no quickCreate)`, async () => {
    Event._views = {
        form: `
            <form>
                <group>
                    <field name="name"/>
                    <field name="start"/>
                    <field name="stop"/>
                    <field name="user_id"/>
                    <field name="partner_id" invisible="1"/>
                </group>
            </form>
        `,
    };
    Event._fields.user_id = fields.Many2one({ relation: "calendar.users", default: 5 });
    Event._fields.partner_id = fields.Many2one({ relation: "calendar.partner", default: 3 });
    CalendarUsers._records.push({ id: 5, name: "user 5", partner_id: 3 });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week" event_open_popup="1" attendee="attendee_ids" color="partner_id">
                <filter name="user_id" avatar_field="image"/>
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="partner_id" filters="1" invisible="1"/>
            </calendar>
        `,
    });

    // dislay all attendee calendars
    await toggleSectionFilter("attendee_ids");
    await toggleFilter("partner_id", 4);
    await checkFilterItems(4);
    expect(`.o_event`).toHaveCount(3);

    // quick create a record
    await selectTimeRange("2016-12-15 06:00:00", "2016-12-15 08:00:00");
    await contains(`.o-calendar-quick-create--input`).edit("coucou", { confirm: false });
    await contains(`.o-calendar-quick-create--edit-btn`).click();
    await contains(`.modal-footer .o_form_button_save`).click();
    await checkFilterItems(5);
    expect(`.o_event`).toHaveCount(4);
});

test(`Toggle multiple values at once in a filter with filter_field`, async () => {
    onRpc("write", ({ args }) => {
        expect.step(`write ${args[0]}`);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id" filter_field="is_checked"/>
            </calendar>
        `,
    });

    await toggleSectionFilter("attendee_ids");
    expect.verifySteps(["write 1,2"]); // single write rpc, on both records
});

test.tags("desktop");
test(`Update event with filters on desktop`, async () => {
    CalendarUsers._records.push({ id: 5, name: "user 5", partner_id: 3 });
    Event._views = {
        form: `
            <form>
                <group>
                    <field name="name"/>
                    <field name="start"/>
                    <field name="stop"/>
                    <field name="user_id"/>
                    <field name="attendee_ids" widget="many2many_tags"/>
                    <field name="partner_id" invisible="1"/>
                </group>
            </form>
        `,
    };

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week" event_open_popup="1" attendee="attendee_ids" color="partner_id">
                <filter name="user_id" avatar_field="image"/>
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="partner_id" filters="1" invisible="1"/>
            </calendar>
        `,
    });

    // select needed partner filters
    await toggleFilter("attendee_ids", 1);
    await toggleFilter("partner_id", 4);
    expect(`.o_calendar_filter_item`).toHaveCount(4);
    expect(`.o_event`).toHaveCount(3);

    await clickEvent(2);
    expect(`.o_cw_popover`).toHaveCount(1);

    await contains(`.o_cw_popover_edit`).click();
    expect(`.modal .modal-title`).toHaveText("Open: event 2");

    await contains(`.modal .o_field_widget[name="user_id"] input`).click();
    await contains(`.ui-autocomplete.dropdown-menu .ui-menu-item:contains(user 5)`).click();
    await contains(`.modal .o_form_button_save`).click();

    expect(`.o_calendar_filter_item`).toHaveCount(5);
    expect(`.o_event`).toHaveCount(3);

    // test the behavior of the 'select all' input checkbox
    expect(`.o_calendar_filter_item input:checked`).toHaveCount(3);
    expect(`.o_calendar_filter_item input:not(:checked)`).toHaveCount(2);

    // Click to select all users
    await toggleSectionFilter("partner_id");

    // should contains 4 events
    expect(`.o_event`).toHaveCount(4);

    // Should have 4 checked boxes
    expect(`.o_calendar_filter_item input:checked`).toHaveCount(4);

    // unselect all user
    await toggleSectionFilter("partner_id");
    expect(`.o_event`).toHaveCount(0);
    expect(`.o_calendar_filter_item input:checked`).toHaveCount(1);
});

test.tags("mobile");
test(`Update event with filters on mobile`, async () => {
    CalendarUsers._records.push({ id: 5, name: "user 5", partner_id: 3 });
    CalendarUsers._views = {
        kanban: `<kanban><templates><t t-name="card"><field name="name"/></t></templates></kanban>`,
    };
    Event._views = {
        form: `
            <form>
                <group>
                    <field name="name"/>
                    <field name="start"/>
                    <field name="stop"/>
                    <field name="user_id"/>
                    <field name="attendee_ids" widget="many2many_tags"/>
                    <field name="partner_id" invisible="1"/>
                </group>
            </form>
        `,
    };

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week" event_open_popup="1" attendee="attendee_ids" color="partner_id">
                <filter name="user_id" avatar_field="image"/>
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="partner_id" filters="1" invisible="1"/>
            </calendar>
        `,
    });
    // select needed partner filters
    await toggleFilter("attendee_ids", 1);
    await toggleFilter("partner_id", 4);
    await checkFilterItems(4);
    expect(`.o_event`).toHaveCount(3);

    await clickEvent(2);
    await contains(`.o_cw_popover_edit`).click();
    expect(`.modal .modal-title`).toHaveText("Open: event 2");

    await contains(`.modal .o_field_widget[name="user_id"] input`).click();
    await animationFrame();
    await contains(`.o_kanban_record:contains(user 5)`).click();
    await contains(`.modal .o_form_button_save`).click();

    await checkFilterItems(5);
    expect(`.o_event`).toHaveCount(3);
    await displayCalendarPanel();

    // test the behavior of the 'select all' input checkbox
    expect(`.o_calendar_filter_item input:checked`).toHaveCount(3);
    expect(`.o_calendar_filter_item input:not(:checked)`).toHaveCount(2);
    await hideCalendarPanel();

    // Click to select all users
    await toggleSectionFilter("partner_id");

    // should contains 4 events
    expect(`.o_event`).toHaveCount(4);
    await displayCalendarPanel();
    // Should have 4 checked boxes
    expect(`.o_calendar_filter_item input:checked`).toHaveCount(4);
    await hideCalendarPanel();
    // unselect all user
    await toggleSectionFilter("partner_id");
    expect(`.o_event`).toHaveCount(0);
    await displayCalendarPanel();
    expect(`.o_calendar_filter_item input:checked`).toHaveCount(1);
});

test.tags("desktop");
test(`change pager with filters`, async () => {
    CalendarUsers._records.push({ id: 5, name: "user 5", partner_id: 3 });
    Event._records.push(
        {
            id: 8,
            user_id: 5,
            partner_id: 3,
            name: "event 8",
            start: "2016-12-06 04:00:00",
            stop: "2016-12-06 08:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
        },
        {
            id: 9,
            user_id: serverState.userId,
            partner_id: 1,
            name: "event 9",
            start: "2016-12-07 04:00:00",
            stop: "2016-12-07 08:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
        },
        {
            id: 10,
            user_id: 4,
            partner_id: 4,
            name: "event 10",
            start: "2016-12-08 04:00:00",
            stop: "2016-12-08 08:00:00",
            is_all_day: false,
            attendee_ids: [1, 2, 3],
        }
    );

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="week" event_open_popup="1" attendee="attendee_ids" color="partner_id">
                <filter name="user_id" avatar_field="image"/>
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="partner_id" filters="1" invisible="1"/>
            </calendar>
        `,
    });

    // select filter for partner 1, 2 and 4
    await toggleSectionFilter("attendee_ids");
    await toggleFilter("partner_id", 4);
    await pickDate("2016-12-05");
    await changeScale("week");
    await checkFilterItems(5);
    expect(`.o_event`).toHaveCount(2);
    expect(queryAllTexts`.fc-event .o_event_title`).toEqual(["event 8", "event 9"]);
});

test.tags("desktop");
test(`events starting at midnight on desktop`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="week"/>`,
    });

    // Click on Tuesday 12am
    await selectTimeRange("2016-12-13 00:00:00", "2016-12-13 00:30:00");
    expect(`.o-calendar-quick-create`).toHaveCount(1);

    // Creating the event
    await contains(`.o-calendar-quick-create--input`).edit("new event in quick create", {
        confirm: false,
    });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect(`.o_event[data-event-id="8"]`).toHaveText("00:00\nnew event in quick create");
});

test.tags("mobile");
test(`events starting at midnight on mobile`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="week"/>`,
    });

    // Click on Tuesday 12am
    await selectTimeRange("2016-12-13 00:00:00", "2016-12-13 00:30:00");
    expect(`.o-calendar-quick-create`).toHaveCount(1);

    // Creating the event
    await contains(`.o-calendar-quick-create--input`).edit("new event in quick create", {
        confirm: false,
    });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect(`.o_event[data-event-id="8"]`).toHaveText("new event in quick create");
});

test(`single day event from midnight to midnight`, async () => {
    mockDate("2016-12-12T08:00:00", 0);
    Event._records = [
        {
            id: 1,
            name: "event 1",
            start: "2016-12-12 00:00:00",
            stop: "2016-12-13 00:00:00",
        },
    ];
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="year"/>`,
    });

    expect(`.o_event`).toHaveCount(1);
    let eventWidth = queryOne(`.o_event`).getBoundingClientRect().width;
    let cellWidth = queryFirst(`.fc-daygrid-day-frame`).getBoundingClientRect().width;
    expect(eventWidth).toBe(cellWidth); // over a single day
    await changeScale("month");
    expect(`.o_event`).toHaveCount(1);
    eventWidth = queryOne(`.o_event`).getBoundingClientRect().width;
    cellWidth = queryFirst(`.fc-daygrid-day-events`).getBoundingClientRect().width;
    expect(eventWidth).not.toBeGreaterThan(cellWidth);
    await changeScale("week");
    expect(`.fc-daygrid-day-events .o_event`).toHaveCount(1);
    eventWidth = queryOne(`.o_event`).getBoundingClientRect().width;
    cellWidth = queryFirst(`.fc-day`).getBoundingClientRect().width;
    expect(eventWidth).not.toBeGreaterThan(cellWidth);
    await changeScale("day");
    expect(`.fc-daygrid-day-events .o_event`).toHaveCount(1);
    await navigate("next");
    expect(`.fc-daygrid-day-events .o_event`).toHaveCount(0);
});

test(`event over two days but lasting less than 24h`, async () => {
    mockDate("2016-12-12T08:00:00", 0);
    Event._records = [
        {
            id: 1,
            name: "event 1",
            start: "2016-12-12 19:00:00",
            stop: "2016-12-13 09:00:00",
        },
    ];
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="year"/>`,
    });

    expect(`.o_event`).toHaveCount(1);
    let eventWidth = queryOne(`.o_event`).getBoundingClientRect().width;
    let cellWidth = queryFirst(`.fc-daygrid-day-frame`).getBoundingClientRect().width;
    expect(eventWidth).toBe(2 * cellWidth); // over 2 days
    await changeScale("month");
    expect(`.o_event`).toHaveCount(1);
    eventWidth = queryOne(`.o_event`).getBoundingClientRect().width;
    cellWidth = queryFirst(`.fc-daygrid-day-events`).getBoundingClientRect().width;
    expect(eventWidth).toBeGreaterThan(cellWidth);
    expect(eventWidth).not.toBeGreaterThan(2 * cellWidth);
    await changeScale("week");
    expect(`.fc-day-mon .o_event`).toHaveCount(1);
    expect(`.fc-day-tue .o_event`).toHaveCount(1);
    await changeScale("day");
    expect(`.fc-day-mon .o_event`).toHaveCount(1);
    await navigate("next");
    expect(`.fc-day-tue .o_event`).toHaveCount(1);
});

test(`event over two days lasting longer than 24h`, async () => {
    mockDate("2016-12-12T08:00:00", 0);
    Event._records = [
        {
            id: 1,
            name: "event 1",
            start: "2016-12-12 09:00:00",
            stop: "2016-12-13 19:00:00",
        },
    ];
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="year"/>`,
    });

    expect(`.o_event`).toHaveCount(1);
    let eventWidth = queryOne(`.o_event`).getBoundingClientRect().width;
    let cellWidth = queryFirst(`.fc-daygrid-day-frame`).getBoundingClientRect().width;
    expect(eventWidth).toBe(2 * cellWidth); // over 2 days
    await changeScale("month");
    expect(`.o_event`).toHaveCount(1);
    eventWidth = queryOne(`.o_event`).getBoundingClientRect().width;
    cellWidth = queryFirst(`.fc-daygrid-day-events`).getBoundingClientRect().width;
    expect(eventWidth).toBeGreaterThan(cellWidth);
    expect(eventWidth).not.toBeGreaterThan(2 * cellWidth);
    await changeScale("week");
    expect(`.fc-daygrid-day-events .o_event`).toHaveCount(1);
    eventWidth = queryOne(`.o_event`).getBoundingClientRect().width;
    cellWidth = queryFirst(`.fc-day`).getBoundingClientRect().width;
    expect(eventWidth).toBeGreaterThan(cellWidth);
    expect(eventWidth).not.toBeGreaterThan(2 * cellWidth);
    await changeScale("day");
    expect(`.fc-daygrid-day-events .o_event`).toHaveCount(1);
    await navigate("next");
    expect(`.fc-daygrid-day-events .o_event`).toHaveCount(1);
});

test(`all day event lasting 2 days`, async () => {
    mockDate("2016-12-12T08:00:00", 0);
    Event._records = [
        {
            id: 1,
            name: "event 1",
            start: "2016-12-12 00:00:00",
            stop: "2016-12-13 00:00:00",
            is_all_day: true,
        },
    ];
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start_date" date_stop="stop_date" all_day="is_all_day" mode="year"/>`,
    });

    expect(`.o_event`).toHaveCount(1);
    let eventWidth = queryOne(`.o_event`).getBoundingClientRect().width;
    let cellWidth = queryFirst(`.fc-daygrid-day-frame`).getBoundingClientRect().width;
    expect(eventWidth).toBe(2 * cellWidth); // over 2 days
    await changeScale("month");
    expect(`.o_event`).toHaveCount(1);
    eventWidth = queryOne(`.o_event`).getBoundingClientRect().width;
    cellWidth = queryFirst(`.fc-daygrid-day-events`).getBoundingClientRect().width;
    expect(eventWidth).toBeGreaterThan(cellWidth);
    expect(eventWidth).not.toBeGreaterThan(2 * cellWidth);
    await changeScale("week");
    expect(`.fc-daygrid-day-events .o_event`).toHaveCount(1);
    eventWidth = queryOne(`.o_event`).getBoundingClientRect().width;
    cellWidth = queryFirst(`.fc-day`).getBoundingClientRect().width;
    expect(eventWidth).toBeGreaterThan(cellWidth);
    expect(eventWidth).not.toBeGreaterThan(2 * cellWidth);
    await changeScale("day");
    expect(`.fc-daygrid-day-events .o_event`).toHaveCount(1);
    await navigate("next");
    expect(`.fc-daygrid-day-events .o_event`).toHaveCount(1);
});

test(`set event as all day when field is date`, async () => {
    mockTimeZone(-8);
    Event._fields.start_date = fields.Date();
    Event._records[0].start_date = "2016-12-14";

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start_date" all_day="is_all_day" mode="week" event_open_popup="1" attendee="attendee_ids" color="partner_id">
                <filter name="user_id" avatar_field="image"/>
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
            </calendar>
        `,
    });

    await toggleFilter("attendee_ids", 1);
    expect(`.fc-daygrid-body .fc-event`).toHaveCount(1);

    await clickEvent(1);
    expect(`.list-group-item:eq(0)`).toHaveText("December 14, 2016");
});

test(`set event as all day when field is date (without all_day mapping)`, async () => {
    Event._fields.start_date = fields.Date();
    Event._records[0].start_date = "2016-12-14";
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start_date" mode="week"/>`,
    });
    expect(`.fc-daygrid-body .fc-event`).toHaveCount(1);
});

test(`set event as all day when field is datetime (without all_day mapping)`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="week"/>`,
    });
    expect(`.fc-daygrid-body .fc-event`).toHaveCount(1, {
        message: "should be one event in the all day row",
    });
});

test(`quickcreate avoid double event creation`, async () => {
    const deferred = new Deferred();

    onRpc("create", async () => {
        expect.step("create");
        await deferred;
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="month" event_open_popup="1"/>`,
    });

    // create a new event
    await clickDate("2016-12-13");
    await contains(`.modal-body input`).edit("new event in quick create", { confirm: false });

    // Simulate ENTER pressed on Create button (after a TAB)
    await press("Enter");
    await click(`.o-calendar-quick-create--create-btn`);
    await animationFrame();

    deferred.resolve();
    await animationFrame();
    expect.verifySteps(["create"]);
});

test(`calendar is configured to have no groupBy menu`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start"/>`,
    });
    expect(`.o_control_panel .o_group_by_menu`).toHaveCount(0);
});

test.tags("desktop");
test(`timezone does not affect current day`, async () => {
    mockTimeZone(40);

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start"/>`,
    });
    expect(`.o_datetime_picker .o_selected`).toHaveText("14");

    await pickDate("2016-12-11");
    expect(`.o_datetime_picker .o_selected`).toHaveText("11");
});

test.tags("desktop");
test(`timezone does not affect drag and drop on desktop`, async () => {
    mockTimeZone(-40);

    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args[0]).toEqual([6]);
        expect(args[1].start).toBe("2016-11-29 08:00:00");
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" mode="month">
                <field name="name"/>
                <field name="start"/>
            </calendar>
        `,
    });

    await clickEvent(1);
    expect(`.o_event[data-event-id="1"]`).toHaveText("08:00\nevent 1");
    expect(`.o_field_widget[name="start"]`).toHaveText("Dec 9, 8:00 AM");

    await clickEvent(6);
    expect(`.o_event[data-event-id="6"]`).toHaveText("16:00\nevent 6");
    expect(`.o_field_widget[name="start"]`).toHaveText("Dec 16, 4:00 PM");

    await closeCwPopOver();
    await moveEventToDate(6, "2016-11-27");
    await clickEvent(6);
    expect(`.o_event[data-event-id="6"]`).toHaveText("16:00\nevent 6");
    expect(`.o_field_widget[name="start"]`).toHaveText("Nov 27, 4:00 PM");
    expect.verifySteps(["write"]);

    await clickEvent(1);
    expect(`.o_event[data-event-id="1"]`).toHaveText("08:00\nevent 1");
    expect(`.o_field_widget[name="start"]`).toHaveText("Dec 9, 8:00 AM");
});

test.tags("mobile");
test(`timezone does not affect drag and drop on mobile`, async () => {
    mockTimeZone(-40);
    patchWithCleanup(CalendarRenderer.prototype, {
        get actionSwiperProps() {
            const props = super.actionSwiperProps;
            props.onLeftSwipe = undefined;
            props.onRightSwipe = undefined;
            return props;
        },
    });
    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args[0]).toEqual([6]);
        expect(args[1].start).toBe("2016-11-29 08:00:00");
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" mode="month">
                <field name="name"/>
                <field name="start"/>
            </calendar>
        `,
    });

    await clickEvent(1);
    expect(`.o_event[data-event-id="1"]`).toHaveText("event 1");
    expect(`.o_field_widget[name="start"]`).toHaveText("Dec 9, 8:00 AM");
    await closeCwPopOver();

    await clickEvent(6);
    expect(`.o_event[data-event-id="6"]`).toHaveText("event 6");
    expect(`.o_field_widget[name="start"]`).toHaveText("Dec 16, 4:00 PM");
    await closeCwPopOver();

    await moveEventToDate(6, "2016-11-27");
    await clickEvent(6);
    expect(`.o_event[data-event-id="6"]`).toHaveText("event 6");
    expect(`.o_field_widget[name="start"]`).toHaveText("Nov 27, 4:00 PM");
    await closeCwPopOver();
    expect.verifySteps(["write"]);

    await clickEvent(1);
    expect(`.o_event[data-event-id="1"]`).toHaveText("event 1");
    expect(`.o_field_widget[name="start"]`).toHaveText("Dec 9, 8:00 AM");
});

test.tags("desktop");
test(`timezone does not affect calendar with date field on desktop`, async () => {
    Event._fields.start_date = fields.Date();
    mockTimeZone(2);

    onRpc("create", ({ args }) => {
        expect.step(`create ${args[0][0].start_date}`);
    });
    onRpc("write", ({ args }) => {
        expect.step(`write ${args[1].start_date}`);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start_date" mode="month">
                <field name="name"/>
                <field name="start_date"/>
            </calendar>
        `,
    });

    await clickDate("2016-12-20");
    await contains(`.o-calendar-quick-create--input`).edit("An event", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect.verifySteps(["create 2016-12-20"]);

    await clickEvent(8);
    expect(`.o_cw_popover`).toHaveCount(1);
    expect(
        `.o_cw_popover .o_cw_popover_fields_secondary .list-group-item .o_field_date`
    ).toHaveText("Dec 20");

    await closeCwPopOver();
    await moveEventToDate(8, "2016-11-27");
    expect.verifySteps(["write 2016-11-27"]);

    await clickEvent(8);
    expect(`.o_cw_popover`).toHaveCount(1);
    expect(
        `.o_cw_popover .o_cw_popover_fields_secondary .list-group-item .o_field_date`
    ).toHaveText("Nov 27");
});

test.tags("mobile");
test(`timezone does not affect calendar with date field on mobile`, async () => {
    Event._fields.start_date = fields.Date();
    mockTimeZone(2);
    patchWithCleanup(CalendarRenderer.prototype, {
        get actionSwiperProps() {
            const props = super.actionSwiperProps;
            props.onLeftSwipe = undefined;
            props.onRightSwipe = undefined;
            return props;
        },
    });
    onRpc("create", ({ args }) => {
        expect.step(`create ${args[0][0].start_date}`);
    });
    onRpc("write", ({ args }) => {
        expect.step(`write ${args[1].start_date}`);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start_date" mode="month">
                <field name="name"/>
                <field name="start_date"/>
            </calendar>
        `,
    });

    await clickDate("2016-12-20");
    await contains(`.o-calendar-quick-create--input`).edit("An event", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect.verifySteps(["create 2016-12-20"]);

    await clickEvent(8);
    expect(`.modal`).toHaveCount(1);
    expect(`.modal .o_cw_popover_fields_secondary .list-group-item .o_field_date`).toHaveText(
        "Dec 20"
    );

    await closeCwPopOver();
    await moveEventToDate(8, "2016-11-27");
    expect.verifySteps(["write 2016-11-27"]);

    await clickEvent(8);
    expect(`.modal`).toHaveCount(1);
    expect(`.modal .o_cw_popover_fields_secondary .list-group-item .o_field_date`).toHaveText(
        "Nov 27"
    );
});

test(`drag and drop on month mode`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" mode="month" event_open_popup="1" quick_create="0">
                <field name="name"/>
                <field name="partner_id"/>
            </calendar>
        `,
    });

    await clickDate("2016-12-20");
    await contains(`.modal-body .o_field_widget[name=name] input`).edit("An event");
    await contains(`.modal .o_form_button_save`).click();
    await moveEventToDate(1, "2016-12-19", { disableDrop: true });
    expect(`.o_event[data-event-id="1"]`).toHaveClass("dayGridMonth");

    await moveEventToDate(8, "2016-12-19");
    await clickEvent(8);
    expect(`.list-group-item:eq(1)`).toHaveText("07:00 - 19:00 (12 hours)");
});

test(`drag and drop on month mode with all_day mapping`, async () => {
    // Same test as before but in calendarEventToRecord (calendar_model.js) there is
    // different condition branching with all_day mapping or not

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" mode="month" event_open_popup="1" quick_create="0" all_day="is_all_day">
                <field name="name"/>
                <field name="partner_id"/>
            </calendar>
        `,
    });

    await clickDate("2016-12-20");
    await contains(`.o_field_widget[name="name"] input`).edit("An event");
    await contains(`.o_field_widget[name="is_all_day"] input`).click();

    // use datepicker to enter a date: 12/20/2016 07:00:00
    await contains(`.o_field_widget[name="start"] button`).click();
    await selectHourOnPicker("7:00");

    // use datepicker to enter a date: 12/20/2016 19:00:00
    await contains(`.o_field_widget[name="stop"] button`).click();
    await selectHourOnPicker("19:00");
    await contains(`.modal .o_form_button_save`).click();
    await moveEventToDate(8, "2016-12-19");
    await clickEvent(8);
    expect(`.list-group-item:eq(1)`).toHaveText("07:00 - 19:00 (12 hours)");
});

test(`drag and drop on month mode with date_start and date_delay`, async () => {
    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args[1].delay).toBe(undefined);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_delay="delay" mode="month">
                <field name="name"/>
                <field name="start"/>
                <field name="delay"/>
            </calendar>
        `,
    });

    await clickDate("2016-12-20");
    await contains(`.o-calendar-quick-create--input`).edit("An event", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    await moveEventToDate(8, "2016-11-27");
    expect.verifySteps(["write"]);
});

test(`form_view_id attribute works (for creating events)`, async () => {
    mockService("action", {
        doAction(request) {
            expect.step("doAction");
            expect(request.views[0][0]).toBe(42);
        },
    });

    onRpc("create", () =>
        // we simulate here the case where a create call with just
        // the field name fails.  This is a normal flow, the server
        // reject the create rpc (quick create), then the web client
        // fall back to a form view. This happens typically when a
        // model has required fields
        Promise.reject("None shall pass!")
    );

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="month" form_view_id="42"/>`,
    });
    await clickDate("2016-12-13");
    await contains(`.modal-body input`).edit("It's just a fleshwound", { confirm: "blur" });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect.verifySteps(["doAction"]);
});

test(`form_view_id attribute works with popup (for creating events)`, async () => {
    mockService("action", {
        doAction(request) {
            expect.step("doAction");
            expect(request.views[0][0]).toBe(1);
        },
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" mode="month" open_event_popup="1" quick_create="0" form_view_id="1">
                <field name="name"/>
            </calendar>
        `,
    });
    await clickDate("2016-12-13");
    expect.verifySteps(["doAction"]);
});

test(`calendar fallback to form view id in action if necessary`, async () => {
    Event._views["form,43"] = /* xml */ `<form />`;

    mockService("action", {
        doAction(request) {
            expect.step("doAction");
            expect(request).toEqual({
                type: "ir.actions.act_window",
                res_model: "event",
                views: [[43, "form"]], // should use the view id from the config
                target: "current",
                context: {
                    lang: "en",
                    uid: serverState.userId,
                    tz: "taht",
                    default_name: "It's just a fleshwound",
                    default_start: "2016-12-13 06:00:00",
                    default_stop: "2016-12-13 18:00:00",
                    default_allday: true,
                    allowed_company_ids: [1],
                },
            });
        },
    });

    onRpc("create", () =>
        // we simulate here the case where a create call with just
        // the field name fails.  This is a normal flow, the server
        // reject the create rpc (quick create), then the web client
        // fall back to a form view. This happens typically when a
        // model has required fields
        Promise.reject("None shall pass!")
    );
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="month"/>`,
        config: { views: [[43, "form"]] },
    });

    await clickDate("2016-12-13");
    await contains(`.modal-body input`).edit("It's just a fleshwound", { confirm: "blur" });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect.verifySteps(["doAction"]);
});

test(`fullcalendar initializes with right locale`, async () => {
    // The machine that runs this test must have this locale available
    serverState.lang = "fr";

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="week"/>`,
    });
    expect(queryAllTexts`.fc-col-header-cell`).toEqual([
        "DIM.\n11",
        "LUN.\n12",
        "MAR.\n13",
        "MER.\n14",
        "JEU.\n15",
        "VEN.\n16",
        "SAM.\n17",
    ]);
});

test(`initial_date given in the context`, async () => {
    Event._views = {
        "calendar,1": `<calendar date_start="start" date_stop="stop" mode="day"/>`,
    };

    defineActions([
        {
            id: 1,
            name: "context initial date",
            res_model: "event",
            views: [[1, "calendar"]],
            context: { initial_date: "2016-01-30 08:00:00" }, // 30th of january
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_breadcrumb`).toHaveText("context initial date");
    expect(`.o_calendar_renderer .fc-col-header-cell .o_cw_day_name`).toHaveText("Saturday");
    expect(`.o_calendar_renderer .fc-col-header-cell .o_cw_day_number`).toHaveText("30");
});

test.tags("desktop");
test(`default week start (US) month mode on desktop`, async () => {
    // if not given any option, default week start is on Sunday
    mockDate("2019-09-12 08:00:00", -7);

    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2019-10-13 06:59:59"],
            ["stop", ">=", "2019-09-01 07:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="month"/>`,
    });
    expect.verifySteps(["event.search_read"]);
    expect(`.fc-col-header-cell .o_cw_day_name:eq(0)`).toHaveText("SUN");
    expect(`.fc-col-header-cell .o_cw_day_name:eq(-1)`).toHaveText("SAT");
    expect(`.fc-daygrid-day:eq(0) .fc-daygrid-week-number`).toHaveText("36");
    expect(`.fc-daygrid-day:eq(0) .fc-daygrid-day-number`).toHaveText("1");
    expect(`.fc-daygrid-day:eq(0)`).toHaveAttribute("data-date", "2019-09-01");
    expect(`.fc-daygrid-day:eq(-1) .fc-daygrid-day-number`).toHaveText("5");
    expect(`.fc-daygrid-day:eq(-1)`).toHaveAttribute("data-date", "2019-10-05");
});

test.tags("mobile");
test(`default week start (US) month mode on mobile`, async () => {
    // if not given any option, default week start is on Sunday
    mockDate("2019-09-12 08:00:00", -7);

    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2019-10-13 06:59:59"],
            ["stop", ">=", "2019-09-01 07:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="month"/>`,
    });
    expect.verifySteps(["event.search_read"]);
    expect(`.fc-col-header-cell .o_cw_day_name:eq(0)`).toHaveText("SUN");
    expect(`.fc-col-header-cell .o_cw_day_name:eq(-1)`).toHaveText("SAT");
    expect(`.o-fc-week:eq(0)`).toHaveText("36");
    expect(`.fc-daygrid-day:eq(0) .fc-daygrid-day-number`).toHaveText("1");
    expect(`.fc-daygrid-day:eq(0)`).toHaveAttribute("data-date", "2019-09-01");
    expect(`.fc-daygrid-day:eq(-1) .fc-daygrid-day-number`).toHaveText("5");
    expect(`.fc-daygrid-day:eq(-1)`).toHaveAttribute("data-date", "2019-10-05");
});

test.tags("desktop");
test(`European week start month mode on chat`, async () => {
    mockDate("2019-09-15 08:00:00");
    // the week start depends on the locale
    defineParams({ lang_parameters: { week_start: 1 } });

    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2019-10-06 22:59:59"],
            ["stop", ">=", "2019-08-25 23:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="month"/>`,
    });
    expect.verifySteps(["event.search_read"]);
    expect(`.fc-col-header-cell .o_cw_day_name:eq(0)`).toHaveText("MON");
    expect(`.fc-col-header-cell .o_cw_day_name:eq(-1)`).toHaveText("SUN");
    expect(`.fc-daygrid-day:eq(0) .fc-daygrid-week-number`).toHaveText("35");
    expect(`.fc-daygrid-day:eq(0) .fc-daygrid-day-number`).toHaveText("26");
    expect(`.fc-daygrid-day:eq(0)`).toHaveAttribute("data-date", "2019-08-26");
    expect(`.fc-daygrid-day:eq(-1) .fc-daygrid-day-number`).toHaveText("6");
    expect(`.fc-daygrid-day:eq(-1)`).toHaveAttribute("data-date", "2019-10-06");
});

test.tags("mobile");
test(`European week start month mode on mobile`, async () => {
    mockDate("2019-09-15 08:00:00");
    // the week start depends on the locale
    defineParams({ lang_parameters: { week_start: 1 } });

    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2019-10-06 22:59:59"],
            ["stop", ">=", "2019-08-25 23:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="month"/>`,
    });
    expect.verifySteps(["event.search_read"]);
    expect(`.fc-col-header-cell .o_cw_day_name:eq(0)`).toHaveText("MON");
    expect(`.fc-col-header-cell .o_cw_day_name:eq(-1)`).toHaveText("SUN");
    expect(`.o-fc-week:eq(0)`).toHaveText("35");
    expect(`.fc-daygrid-day:eq(0) .fc-daygrid-day-number`).toHaveText("26");
    expect(`.fc-daygrid-day:eq(0)`).toHaveAttribute("data-date", "2019-08-26");
    expect(`.fc-daygrid-day:eq(-1) .fc-daygrid-day-number`).toHaveText("6");
    expect(`.fc-daygrid-day:eq(-1)`).toHaveAttribute("data-date", "2019-10-06");
});

test.tags("desktop");
test(`Monday week start week mode on desktop`, async () => {
    mockDate("2019-09-15 08:00:00");
    // the week start depends on the locale
    defineParams({ lang_parameters: { week_start: 1 } });

    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2019-09-15 22:59:59"],
            ["stop", ">=", "2019-09-08 23:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="week"/>`,
    });
    expect.verifySteps(["event.search_read"]);
    expect(`.fc-timeGridWeek-view .fc-daygrid-body`).toHaveCount(1);
    expect(`.fc-col-header-cell .o_cw_day_name:eq(0)`).toHaveText("MON");
    expect(`.fc-col-header-cell .o_cw_day_number:eq(0)`).toHaveText("9");
    expect(`.fc-col-header-cell .o_cw_day_name:eq(-1)`).toHaveText("SUN");
    expect(`.fc-col-header-cell .o_cw_day_number:eq(-1)`).toHaveText("15");
    expect(`.fc-timegrid-axis-cushion:eq(0)`).toHaveText("Week 37");
});

test.tags("mobile");
test(`Monday week start week mode on mobile`, async () => {
    mockDate("2019-09-15 08:00:00");
    // the week start depends on the locale
    defineParams({ lang_parameters: { week_start: 1 } });

    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2019-09-15 22:59:59"],
            ["stop", ">=", "2019-09-08 23:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="week"/>`,
    });
    expect.verifySteps(["event.search_read"]);
    expect(`.fc-timeGridWeek-view .fc-daygrid-body`).toHaveCount(1);
    expect(`.fc-col-header-cell .o_cw_day_name:eq(0)`).toHaveText("MON");
    expect(`.fc-col-header-cell .o_cw_day_number:eq(0)`).toHaveText("9");
    expect(`.fc-col-header-cell .o_cw_day_name:eq(-1)`).toHaveText("SUN");
    expect(`.fc-col-header-cell .o_cw_day_number:eq(-1)`).toHaveText("15");
    expect(`.fc-timegrid-axis-cushion:eq(0)`).toHaveText("37");
    expect(`.o_calendar_header .badge`).toHaveText("Week 37");
});

test.tags("desktop");
test(`Saturday week start week mode on desktop`, async () => {
    mockDate("2019-09-12 08:00:00");
    // the week start depends on the locale
    defineParams({ lang_parameters: { week_start: 6 } });

    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2019-09-13 22:59:59"],
            ["stop", ">=", "2019-09-06 23:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="week"/>`,
    });
    expect.verifySteps(["event.search_read"]);
    expect(`.fc-timeGridWeek-view .fc-daygrid-body`).toHaveCount(1);
    expect(`.fc-col-header-cell .o_cw_day_name:eq(0)`).toHaveText("SAT");
    expect(`.fc-col-header-cell .o_cw_day_number:eq(0)`).toHaveText("7");
    expect(`.fc-col-header-cell .o_cw_day_name:eq(-1)`).toHaveText("FRI");
    expect(`.fc-col-header-cell .o_cw_day_number:eq(-1)`).toHaveText("13");
    expect(`.fc-timegrid-axis-cushion:eq(0)`).toHaveText("Week 37");
});

test.tags("mobile");
test(`Saturday week start week mode on mobile`, async () => {
    mockDate("2019-09-12 08:00:00");
    // the week start depends on the locale
    defineParams({ lang_parameters: { week_start: 6 } });

    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2019-09-13 22:59:59"],
            ["stop", ">=", "2019-09-06 23:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="week"/>`,
    });
    expect.verifySteps(["event.search_read"]);
    expect(`.fc-timeGridWeek-view .fc-daygrid-body`).toHaveCount(1);
    expect(`.fc-col-header-cell .o_cw_day_name:eq(0)`).toHaveText("SAT");
    expect(`.fc-col-header-cell .o_cw_day_number:eq(0)`).toHaveText("7");
    expect(`.fc-col-header-cell .o_cw_day_name:eq(-1)`).toHaveText("FRI");
    expect(`.fc-col-header-cell .o_cw_day_number:eq(-1)`).toHaveText("13");
    expect(`.fc-timegrid-axis-cushion:eq(0)`).toHaveText("37");
    expect(`.o_calendar_header .badge`).toHaveText("Week 37");
});

test(`Monday week start year mode`, async () => {
    mockDate("2019-09-15 08:00:00");
    // the week start depends on the locale
    defineParams({ lang_parameters: { week_start: 1 } });

    patchWithCleanup(CalendarYearRenderer.prototype, {
        get options() {
            return { ...super.options, weekNumbers: true };
        },
    });

    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2019-12-31 22:59:59"],
            ["stop", ">=", "2018-12-31 23:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="year"/>`,
    });
    expect.verifySteps(["event.search_read"]);

    const weekRow = queryFirst(`.fc-day-today`).closest("tr");
    expect(queryFirst(`.fc-daygrid-day-top`, { root: weekRow })).toHaveText("9", {
        message: "The first day of the week should be Monday the 9th",
    });
    expect(queryOne(`.fc-daygrid-day-top:last`, { root: weekRow })).toHaveText("15", {
        message: "The last day of the week should be Sunday the 15th",
    });
    expect(queryFirst(`.fc-daygrid-week-number`, { root: weekRow })).toHaveText("37");
});

test(`Sunday week start year mode`, async () => {
    mockDate("2019-09-15 08:00:00");
    // the week start depends on the locale
    // the localization presents a python-like 1 to 7 weekStart value
    defineParams({ lang_parameters: { week_start: 7 } });

    patchWithCleanup(CalendarYearRenderer.prototype, {
        get options() {
            return { ...super.options, weekNumbers: true };
        },
    });

    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2019-12-31 22:59:59"],
            ["stop", ">=", "2018-12-31 23:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" mode="year"/>`,
    });
    expect.verifySteps(["event.search_read"]);

    const weekRow = queryFirst(`.fc-day-today`).closest("tr");
    expect(queryFirst(`.fc-daygrid-day-top`, { root: weekRow })).toHaveText("15", {
        message: "The first day of the week should be Sunday the 15th",
    });
    expect(queryOne(`.fc-daygrid-day-top:last`, { root: weekRow })).toHaveText("21", {
        message: "The last day of the week should be Saturday the 21st",
    });
    expect(queryFirst(`.fc-daygrid-week-number`, { root: weekRow })).toHaveText("38");
});

test(`edit record and attempt to create a record with "create" attribute set to false`, async () => {
    onRpc("web_save", ({ args }) => {
        expect.step("save");
        expect(args[1]).toEqual({ name: "event 4 modified" });
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar event_open_popup="1" create="0" date_start="start" date_stop="stop" mode="month"/>`,
    });

    // editing existing events should still be possible
    // click on an existing event to open the formViewDialog
    await clickEvent(4);
    const popover = getMockEnv().isSmall ? ".modal" : ".o_cw_popover";
    const closeButton = getMockEnv().isSmall ? ".oi-arrow-left" : ".o_cw_popover_close";
    expect(popover).toHaveCount(1);
    expect(`${popover} .o_cw_popover_edit`).toHaveCount(1);
    expect(`${popover} .o_cw_popover_delete`).toHaveCount(1);
    expect(`${popover} ${closeButton}`).toHaveCount(1);

    await contains(`${popover} .o_cw_popover_edit`).click();
    expect(`.modal-body`).toHaveCount(1);

    await contains(`.modal-body input`).edit("event 4 modified");
    await contains(`.modal-footer .o_form_button_save`).click();
    expect(`.modal`).toHaveCount(0);
    expect.verifySteps(["save"]);

    // creating an event should not be possible
    // attempt to create a new event with create set to false
    await clickDate("2016-12-13");
    expect(`.modal`).toHaveCount(0, {
        message:
            "shouldn't open a quick create dialog for creating a new event with create attribute set to false",
    });
});

test(`attempt to create record with "create" and "quick_add" attributes set to false`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar create="0" event_open_popup="1" quick_create="0" date_start="start" date_stop="stop" mode="month"/>`,
    });
    await clickDate("2016-12-13");
    expect(`.modal`).toHaveCount(0, {
        message:
            "shouldn't open a form view for creating a new event with create attribute set to false",
    });
});

test(`attempt to create multiples events and the same day and check the ordering on month view`, async () => {
    // This test aims to verify that the order of the event in month view is coherent with their start date.
    mockDate("2020-03-12 08:00:00");

    Event._records = [
        {
            id: 1,
            name: "Second event",
            start: "2020-03-12 05:00:00",
            stop: "2020-03-12 07:00:00",
            is_all_day: false,
        },
        {
            id: 2,
            name: "First event",
            start: "2020-03-12 02:00:00",
            stop: "2020-03-12 03:00:00",
            is_all_day: false,
        },
        {
            id: 3,
            name: "Third event",
            start: "2020-03-12 08:00:00",
            stop: "2020-03-12 09:00:00",
            is_all_day: false,
        },
    ];

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="month"/>`,
    });
    expect(`.o_calendar_renderer .fc-view`).toHaveCount(1);
    expect(queryAllTexts`.o_event_title`).toEqual(["First event", "Second event", "Third event"]);
});

test.tags("desktop");
test(`Resizing Pill of Multiple Days(Allday)`, async () => {
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({
            is_all_day: true,
            name: "foobar",
            start: "2016-12-13 00:00:00",
            start_date: false,
            stop: "2016-12-14 00:00:00",
            stop_date: false,
        });
    });

    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args[1]).toEqual({
            is_all_day: true,
            start: "2016-12-13",
            stop: "2016-12-16",
        });
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar event_open_popup="1" quick_create="0" date_start="start" date_stop="stop" all_day="is_all_day" mode="month"/>`,
    });

    await selectDateRange("2016-12-13", "2016-12-14");
    await contains(`.modal .o_field_widget[name="name"] input`).edit("foobar", { confirm: false });
    await contains(`.modal .o_form_button_save`).click();
    expect.verifySteps(["web_save"]);

    await resizeEventToDate(8, "2016-12-16");
    const event = queryFirst`.o_event[data-event-id="8"]`;
    expect(event).toHaveText("foobar");
    expect(event.closest(".fc-daygrid-day")).not.toBeEmpty();
    expect.verifySteps(["write"]);
});

test.tags("desktop");
test(`create event and resize to next day (24h) on week mode`, async () => {
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({
            is_all_day: false,
            name: "foobar",
            start: "2016-12-13 07:00:00",
            start_date: false,
            stop: "2016-12-13 15:00:00",
            stop_date: false,
        });
    });
    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args[1]).toEqual({
            is_all_day: false,
            start: "2016-12-13 07:00:00",
            stop: "2016-12-14 07:00:00",
        });
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar event_open_popup="1" quick_create="0" date_start="start" date_stop="stop" all_day="is_all_day" mode="week"/>`,
    });

    await selectTimeRange("2016-12-13 08:00:00", "2016-12-13 16:00:00");
    await contains(`.modal .o_field_widget[name="name"] input`).edit("foobar", { confirm: false });
    await contains(`.modal .o_form_button_save`).click();
    expect.verifySteps(["web_save"]);

    await resizeEventToTime(8, "2016-12-14 08:00:00");
    const event = queryFirst`.o_event[data-event-id="8"]`;
    expect(event).toHaveText("foobar");
    expect(event.closest(".fc-daygrid-day")).not.toBeEmpty();
    expect.verifySteps(["write"]);
});

test.tags("desktop");
test(`correctly display year view`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar create="0" event_open_popup="1" date_start="start" date_stop="stop" all_day="is_all_day" mode="year" attendee="attendee_ids" color="partner_id">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="partner_id" filters="1" invisible="1"/>
                <field name="is_hatched" invisible="1"/>
                <field name="is_striked" invisible="1"/>
            </calendar>
        `,
    });

    await toggleFilter("attendee_ids", 1);
    await toggleFilter("attendee_ids", 2);

    expect(`.fc-month`).toHaveCount(12);
    expect(queryAllTexts`.fc-month .fc-header-toolbar`).toEqual([
        "January 2016",
        "February 2016",
        "March 2016",
        "April 2016",
        "May 2016",
        "June 2016",
        "July 2016",
        "August 2016",
        "September 2016",
        "October 2016",
        "November 2016",
        "December 2016",
    ]);
    expect(`.fc-bg-event`).toHaveCount(7); // There should be 6 events displayed but there is 1 split on 2 weeks
    expect(`.o_event_hatched`).toHaveCount(3);
    expect(`.o_event_striked`).toHaveCount(1);

    await clickDate("2016-11-17");
    expect(`.o_popover`).toHaveCount(0);

    await clickDate("2016-11-16");
    expect(`.o_popover`).toHaveCount(1);
    expect(`.o_popover`).toHaveText("November 14-16, 2016\nevent 7");

    await closeCwPopOver();
    expect(`.o_popover`).toHaveCount(0);

    await clickDate("2016-11-14");
    expect(`.o_popover`).toHaveCount(1);
    expect(`.o_popover`).toHaveText("November 14-16, 2016\nevent 7");

    await closeCwPopOver();
    expect(`.o_popover`).toHaveCount(0);

    await clickDate("2016-11-13");
    expect(`.o_popover`).toHaveCount(0);

    await clickDate("2016-12-10");
    expect(`.o_popover`).toHaveCount(0);

    await clickDate("2016-12-12");
    expect(`.o_popover`).toHaveCount(1);
    expect(`.o_popover`).toHaveText("December 12, 2016\n11:55\nevent 2\n16:55\nevent 3");

    await closeCwPopOver();
    expect(`.o_popover`).toHaveCount(0);

    await clickDate("2016-12-14");
    expect(`.o_popover`).toHaveCount(1);
    expect(`.o_popover`).toHaveText("December 14, 2016\nevent 4\nDecember 13-20, 2016\nevent 5");

    await closeCwPopOver();
    expect(`.o_popover`).toHaveCount(0);

    await clickDate("2016-12-21");
    expect(`.o_popover`).toHaveCount(0);
});

test(`toggle filters in year view`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="is_all_day" mode="year" attendee="attendee_ids" color="partner_id">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id"/>
                <field name="partner_id" filters="1" invisible="1"/>
            </calendar>
        `,
    });

    // activate partner filter
    await toggleFilter("attendee_ids", 1);
    await toggleFilter("attendee_ids", 2);
    expect(`.fc-bg-event[data-event-id="1"]`).toHaveCount(1);
    expect(`.fc-bg-event[data-event-id="2"]`).toHaveCount(1);
    expect(`.fc-bg-event[data-event-id="3"]`).toHaveCount(1);
    expect(`.fc-bg-event[data-event-id="4"]`).toHaveCount(1);
    expect(`.fc-bg-event[data-event-id="5"]`).toHaveCount(2);
    expect(`.fc-bg-event[data-event-id="6"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="7"]`).toHaveCount(1);

    await toggleFilter("attendee_ids", 2);
    expect(`.fc-bg-event[data-event-id="1"]`).toHaveCount(1);
    expect(`.fc-bg-event[data-event-id="2"]`).toHaveCount(1);
    expect(`.fc-bg-event[data-event-id="3"]`).toHaveCount(1);
    expect(`.fc-bg-event[data-event-id="4"]`).toHaveCount(1);
    expect(`.fc-bg-event[data-event-id="5"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="6"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="7"]`).toHaveCount(0);

    await toggleFilter("partner_id", 1);
    expect(`.fc-bg-event[data-event-id="1"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="2"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="3"]`).toHaveCount(1);
    expect(`.fc-bg-event[data-event-id="4"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="5"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="6"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="7"]`).toHaveCount(0);

    await toggleFilter("partner_id", 4);
    expect(`.fc-bg-event[data-event-id="1"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="2"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="3"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="4"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="5"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="6"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="7"]`).toHaveCount(0);

    await toggleFilter("attendee_ids", 1);
    expect(`.fc-bg-event[data-event-id="1"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="2"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="3"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="4"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="5"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="6"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="7"]`).toHaveCount(0);

    await toggleFilter("attendee_ids", 2);
    expect(`.fc-bg-event[data-event-id="1"]`).toHaveCount(1);
    expect(`.fc-bg-event[data-event-id="2"]`).toHaveCount(1);
    expect(`.fc-bg-event[data-event-id="3"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="4"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="5"]`).toHaveCount(2);
    expect(`.fc-bg-event[data-event-id="6"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="7"]`).toHaveCount(1);

    await toggleFilter("partner_id", 4);
    expect(`.fc-bg-event[data-event-id="1"]`).toHaveCount(1);
    expect(`.fc-bg-event[data-event-id="2"]`).toHaveCount(1);
    expect(`.fc-bg-event[data-event-id="3"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="4"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="5"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="6"]`).toHaveCount(0);
    expect(`.fc-bg-event[data-event-id="7"]`).toHaveCount(1);
});

test(`allowed scales`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop" all_day="is_all_day" scales="day,week"/>`,
    });

    await contains(`.o_view_scale_selector .scale_button_selection`).click();
    expect(`.o-dropdown--menu .o_scale_button_day`).toHaveCount(1);
    expect(`.o-dropdown--menu .o_scale_button_week`).toHaveCount(1);
    expect(`.o-dropdown--menu .o_scale_button_month`).toHaveCount(0);
    expect(`.o-dropdown--menu .o_scale_button_year`).toHaveCount(0);
});

test.tags("desktop");
test(`click outside the popup should close it`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar create="0" event_open_popup="1" quick_create="0" date_start="start" date_stop="stop" all_day="is_all_day" mode="month"/>`,
    });
    expect(`.o_cw_popover`).toHaveCount(0);

    await clickEvent(1);
    expect(`.o_cw_popover`).toHaveCount(1);

    await contains(`.o_cw_popover .o_cw_body`).click();
    expect(`.o_cw_popover`).toHaveCount(1);

    await contains(`.o_calendar_view`).click();
    expect(`.o_cw_popover`).toHaveCount(0);
});

test(`fields are added in the right order in popover`, async () => {
    const deferred = new Deferred();
    class DeferredWidget extends Component {
        static template = xml``;
        static props = ["*"];
        setup() {
            onWillStart(() => deferred);
        }
    }
    registry.category("fields").add("deferred_widget", { component: DeferredWidget });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="month">
                <field name="user_id" widget="deferred_widget"/>
                <field name="name"/>
            </calendar>
        `,
    });

    await clickEvent(4);
    const popover = getMockEnv().isSmall ? ".modal" : ".o_cw_popover";
    expect(popover).toHaveCount(0);

    deferred.resolve();
    await animationFrame();
    expect(popover).toHaveCount(1);
    expect(`${popover} .o_cw_popover_fields_secondary`).toHaveText("User\nName\nevent 4");
});

test(`select events and discard create`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="is_all_day" mode="year"/>`,
    });
    expect(`.fc-dayGridMonth-view`).toHaveCount(12);

    await selectDateRange("2016-11-13", "2016-11-19");
    expect(`.o-calendar-quick-create`).toHaveCount(1);
    expectEventToBeOver(`.fc-highlight`, [["2016-11-13", "2016-11-19"]]);

    await contains(`.o-calendar-quick-create--cancel-btn`).click();
    expect(`.fc-highlight`).toHaveCount(0);
});

test.tags("desktop");
test(`create event in year view`, async () => {
    onRpc("create", ({ args }) => {
        expect.step(args[0][0]);
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="is_all_day" mode="year"/>`,
    });

    // Select the whole month of July
    await selectDateRange("2016-07-01", "2016-07-31");
    await contains(`.o-calendar-quick-create--input[name=title]`).edit("Whole July", {
        confirm: false,
    });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect.verifySteps([
        { name: "Whole July", is_all_day: true, start: "2016-07-01", stop: "2016-07-31" },
    ]);

    // get all rows for event 8
    expect(`.o_event[data-event-id='8']`).toHaveCount(6);
    expectEventToBeOver(`.o_event[data-event-id='8']`, [
        ["2016-07-01", "2016-07-02"],
        ["2016-07-03", "2016-07-09"],
        ["2016-07-10", "2016-07-16"],
        ["2016-07-17", "2016-07-23"],
        ["2016-07-24", "2016-07-30"],
        ["2016-07-31", "2016-07-31"],
    ]);

    // Select the whole month of November
    await selectDateRange("2016-11-01", "2016-11-30");
    await contains(`.o-calendar-quick-create--input[name=title]`).edit("Whole November", {
        confirm: false,
    });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect.verifySteps([
        { name: "Whole November", is_all_day: true, start: "2016-11-01", stop: "2016-11-30" },
    ]);

    // get all rows for event 9
    expect(`.o_event[data-event-id='9']`).toHaveCount(5);
    expectEventToBeOver(`.o_event[data-event-id='9']`, [
        ["2016-11-01", "2016-11-05"],
        ["2016-11-06", "2016-11-12"],
        ["2016-11-13", "2016-11-19"],
        ["2016-11-20", "2016-11-26"],
        ["2016-11-27", "2016-11-30"],
    ]);
});

test(`popover ignores readonly field modifier`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="month">
                <field name="delay" invisible="True"/>
                <field name="name" readonly="delay == 42"/>
            </calendar>
        `,
    });

    await clickEvent(4);
    // test would fail here if we don't ignore readonly modifier
    const popover = getMockEnv().isSmall ? ".modal" : ".o_cw_popover";
    expect(popover).toHaveCount(1);
});

test.tags("desktop");
test(`calendar with option show_date_picker set to false and no filter`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" show_date_picker="0">
                <field name="name"/>
            </calendar>
        `,
    });
    expect(`.o_datetime_picker`).toHaveCount(0);
    expect(`.o_calendar_sidebar`).toHaveCount(0);
    expect(`.o_sidebar_toggler`).toHaveCount(0);
});

test.tags("desktop");
test(`calendar with option show_date_picker set to false and filters`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" show_date_picker="0">
                <field name="name"/>
                <field name="partner_id" filters="1"/>
            </calendar>
        `,
    });
    expect(`.o_datetime_picker`).toHaveCount(0);
    expect(`.o_calendar_sidebar`).toHaveCount(1);
    expect(`.o_sidebar_toggler`).toHaveCount(1);
});

test(`calendar with option month_overflow not set (default)`, async () => {
    Event._records = [
        {
            id: 1,
            name: "event november",
            start: "2016-11-30 10:00:00",
            stop: "2016-11-30 15:00:00",
            user_id: serverState.userId,
            partner_id: 1,
        },
        {
            id: 2,
            name: "event december",
            start: "2016-12-14 10:00:00",
            stop: "2016-12-14 15:00:00",
            user_id: serverState.userId,
            partner_id: 1,
        },
    ];

    onRpc("search_read", ({ kwargs }) => {
        expect.step("search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2017-01-07 22:59:59"],
            ["start", ">=", "2016-11-26 23:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" mode="month">
                <field name="name"/>
            </calendar>
        `,
    });
    expect(`.o_event`).toHaveCount(2);
    expect(".fc-day-disabled").toHaveCount(0);
    expect.verifySteps(["search_read"]);
});

test(`calendar with option month_overflow set to false`, async () => {
    Event._records = [
        {
            id: 1,
            name: "event november",
            start: "2016-11-30 10:00:00",
            stop: "2016-11-30 15:00:00",
            user_id: serverState.userId,
            partner_id: 1,
        },
        {
            id: 2,
            name: "event december",
            start: "2016-12-14 10:00:00",
            stop: "2016-12-14 15:00:00",
            user_id: serverState.userId,
            partner_id: 1,
        },
        {
            id: 3,
            name: "event january",
            start: "2017-01-02 10:00:00",
            stop: "2016-01-02 15:00:00",
            user_id: serverState.userId,
            partner_id: 1,
        },
    ];

    onRpc("search_read", ({ kwargs }) => {
        expect.step("search_read");
        expect(kwargs.domain).toEqual([
            ["start", "<=", "2016-12-31 22:59:59"],
            ["start", ">=", "2016-11-30 23:00:00"],
        ]);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" mode="month" month_overflow="0">
                <field name="name"/>
            </calendar>
        `,
    });
    expect(".o_event").toHaveCount(1);
    expect(".fc-day-disabled").toHaveCount(4);
    expect.verifySteps(["search_read"]);
});

test.tags("desktop");
test(`can not select invalid scale from datepicker`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="month" scales="month,year">
                <field name="delay" invisible="True"/>
                <field name="name" readonly="delay == 42"/>
            </calendar>
        `,
    });

    await contains(`.o_datetime_picker .o_today`).click();
    // test would fail here if we went to week mode
    expect(`.fc-dayGridMonth-view`).toHaveCount(1);
});

test(`calendar with custom quick create view`, async () => {
    mockService("dialog", {
        add(_, props) {
            expect.step(`add dialog ${props.viewId}`);
            return () => {};
        },
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" all_day="is_all_day" mode="month" quick_create="1" quick_create_view_id="2">
                <field name="name"/>
            </calendar>
        `,
    });
    await clickAllDaySlot("2016-12-01");
    expect.verifySteps(["add dialog 2"]);
});

test(`check apply default record label`, async () => {
    class TestCalendarController extends CalendarController {
        get editRecordDefaultDisplayText() {
            return "Test Display";
        }
    }

    registry.category("views").add("test_calendar_view", {
        ...calendarView,
        Controller: TestCalendarController,
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar js_class="test_calendar_view" date_start="start" date_stop="stop" all_day="is_all_day" mode="month" quick_create="0" event_open_popup="1"/>`,
    });

    await clickDate("2016-12-13");
    expect(`.modal-title`).toHaveText("Test Display");
});

test(`calendar render properties in popover`, async () => {
    Event._fields.properties = fields.Properties({
        definition_record: "type_id",
        definition_record_field: "definitions",
    });
    Event._records[0].type_id = 1;
    Event._records[0].properties = {
        property_1: "hello",
        property_2: "b",
        property_3: "hidden",
    };

    EventType._fields.definitions = fields.PropertiesDefinition();
    EventType._records[0].definitions = [
        {
            name: "property_1",
            string: "My Char",
            type: "char",
            view_in_cards: true,
        },
        {
            name: "property_2",
            string: "My Selection",
            type: "selection",
            selection: [
                ["a", "A"],
                ["b", "B"],
                ["c", "C"],
            ],
            default: "c",
            view_in_cards: true,
        },
        {
            name: "property_3",
            string: "Hidden Char",
            type: "char",
            view_in_cards: false,
        },
    ];

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar quick_create="0" event_open_popup="1" date_start="start">
                <field name="type_id"/>
                <field name="properties"/>
            </calendar>
        `,
    });

    await clickEvent(1);
    const popover = getMockEnv().isSmall ? ".modal" : ".o_popover";
    // Labels:
    expect(queryAllTexts(`${popover} .o_calendar_property_field span.fw-bold`)).toEqual([
        "My Char",
        "My Selection",
    ]);
    // Values:
    expect(queryAllTexts(`${popover} .o_calendar_property_field div.text-truncate`)).toEqual([
        "hello",
        "B",
    ]);
});

test(`calendar create record with default properties`, async () => {
    Event._fields.properties = fields.Properties({
        definition_record: "type_id",
        definition_record_field: "definitions",
    });
    Event._views = {
        form: `
            <form>
                <group>
                    <field name="name"/>
                    <field name="type_id"/>
                    <field name="properties"/>
                </group>
            </form>
        `,
    };

    EventType._fields.definitions = fields.PropertiesDefinition();

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar quick_create="0" event_open_popup="1" date_start="start">
                <field name="type_id"/>
                <field name="properties"/>
            </calendar>
        `,
        context: {
            default_properties: [{ name: "event_prop", string: "Hello", type: "char" }],
        },
    });
    await selectTimeRange("2016-12-15 06:00:00", "2016-12-15 08:00:00");
    expect(`.modal`).toHaveCount(1);
    expect(`.modal [name='properties']`).toHaveText("Hello");
});

test(`calendar show past events with background blur`, async () => {
    mockDate("2016-12-14 09:00:00");

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="week"/>`,
    });
    expect(`.o_event`).toHaveCount(5);
    expect(`.fc-event.o_past_event`).toHaveCount(4);
});

test.tags("desktop");
test(`calendar sidebar state is saved on session storage`, async () => {
    patchWithCleanup(sessionStorage, {
        setItem(key, value) {
            if (key === "calendar.showSideBar") {
                expect.step(`${key}-${value}`);
            }
        },
        getItem(key) {
            if (key === "calendar.showSideBar") {
                expect.step(`${key}-read`);
                return false;
            }
        },
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="week"/>`,
    });
    expect(`.o_calendar_sidebar`).toHaveCount(0);

    await contains(`.o_sidebar_toggler .oi-panel-right`).click();
    expect(`.o_calendar_sidebar`).toHaveCount(1);
    expect.verifySteps(["calendar.showSideBar-read", "calendar.showSideBar-true"]);
});

test(`calendar should show date information on header`, async () => {
    mockDate("2015-12-26 09:00:00");

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="week"/>`,
    });
    expect(`.o_calendar_header h5`).toHaveText("December 2015\nWeek 52");

    await changeScale("day");
    expect(`.o_calendar_header h5`).toHaveText("26 December 2015");

    await changeScale("month");
    expect(`.o_calendar_header h5`).toHaveText("December 2015");

    await changeScale("year");
    expect(`.o_calendar_header h5`).toHaveText("2015");

    await changeScale("week");
    await navigate("next");
    expect(`.o_calendar_header h5`).toHaveText("December 2015 - January 2016\nWeek 53");

    await navigate("prev");
    await navigate("prev");
    await navigate("prev");
    await navigate("prev");
    expect(`.o_calendar_header h5`).toHaveText("November - December 2015\nWeek 49");
});

test(`calendar sidebar filters are ASC sorted (not valued @end)`, async () => {
    mockDate("2023-12-14 09:00:00");

    Event._records = [];
    for (let i = 1; i <= 18; i++) {
        Event._records.push({
            user_id: i,
            name: `event ${i}`,
            start: "2023-12-11 00:00:00",
            stop: "2023-12-11 00:00:00",
        });
    }
    Event._records.push({
        user_id: false,
        name: `event X`,
        start: "2023-12-11 00:00:00",
        stop: "2023-12-11 00:00:00",
    });

    CalendarUsers._records = [
        { id: 1, name: "Zoooro" },
        { id: 2, name: "Jean-Paul 1" },
        { id: 3, name: "Jean-Paul 2" },
        { id: 4, name: "Jeremy" },
        { id: 5, name: "Kévin" },
        { id: 6, name: "Romelü" },
        { id: 7, name: "Edên" },
        { id: 8, name: "Thibaùlt" },
        { id: 9, name: "1 - brol" },
        { id: 10, name: "10 - machin" },
        { id: 11, name: "11 - chose" },
        { id: 12, name: "101" },
        { id: 13, name: "100 - bidule" },
        { id: 14, name: "1000 - truc" },
        { id: 15, name: "00 - bazar" },
        { id: 16, name: "0 - chouette" },
        { id: 17, name: "@Hello" },
        { id: 18, name: "#Hello" },
    ];

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" mode="month">
                <field name="user_id" filters="1"/>
            </calendar>
        `,
    });
    await displayCalendarPanel();
    expect(queryAllTexts`.o_calendar_filter_items .o_cw_filter_title`).toEqual([
        "00 - bazar",
        "0 - chouette",
        "1 - brol",
        "10 - machin",
        "11 - chose",
        "100 - bidule",
        "101",
        "1000 - truc",
        "Edên",
        "@Hello",
        "#Hello",
        "Jean-Paul 1",
        "Jean-Paul 2",
        "Jeremy",
        "Kévin",
        "Romelü",
        "Thibaùlt",
        "Zoooro",
        "Undefined",
    ]);
});

test("sample data are not removed when switching back from calendar view", async () => {
    Event._records = [];
    Event._views = {
        calendar: `<calendar date_start="start" date_stop="stop" mode="day"/>`,
        list: `
            <list sample="1">
                <field name="start"/>
                <field name="stop"/>
            </list>
        `,
    };

    defineActions([
        {
            id: 1,
            name: "Partners",
            res_model: "event",
            views: [
                [false, "list"],
                [false, "calendar"],
            ],
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_list_view`).toHaveCount(1);
    expect(`.o_view_sample_data`).toHaveCount(1);

    await getService("action").switchView("calendar");
    expect(`.o_calendar_container`).toHaveCount(1);

    await getService("action").switchView("list");
    expect(`.o_list_view`).toHaveCount(1);
    expect(`.o_view_sample_data`).toHaveCount(1);
});

test(`Scale: scale default is fetched from localStorage`, async () => {
    patchWithCleanup(localStorage, {
        getItem(key) {
            if (key.startsWith("scaleOf-viewId")) {
                return "week";
            }
        },
        setItem(key, value) {
            if (key === "scaleOf-viewId-19") {
                expect.step(`scale_${value}`);
            }
        },
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" mode="month"/>`,
        viewId: 19,
    });
    expect.verifySteps(["scale_week"]);
    expect(`.scale_button_selection`).toHaveText("Week");

    await changeScale("year");
    expect(`.scale_button_selection`).toHaveText("Year");
    expect.verifySteps(["scale_year"]);
});

test.tags("desktop");
test(`scroll to current hour when clicking on today`, async () => {
    mockDate("2016-12-12T01:00:00", 1);
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="is_all_day" mode="week"/>`,
    });
    // Default scroll time should be 6am no matter the current hour
    expect(queryOne(".fc-scroller:last").scrollTop).toBeWithin(210, 230);
    await contains(".o_calendar_button_today").click();
    expect(queryOne(".fc-scroller:last").scrollTop).toBe(0);
    mockDate("2016-12-12T20:00:00", 1);
    await contains(".o_calendar_button_today").click();
    expect(queryOne(".fc-scroller:last").scrollTop).toBeWithin(360, 380);
});

test("save selected date during view switching", async () => {
    defineActions([
        {
            id: 1,
            name: "Partners",
            res_model: "event",
            views: [
                [false, "list"],
                [false, "calendar"],
            ],
        },
    ]);

    Event._views = {
        calendar: `<calendar date_start="start" date_stop="stop" mode="week"/>`,
        list: `
            <list sample="1">
                <field name="start"/>
                <field name="stop"/>
            </list>
        `,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    await getService("action").switchView("calendar");
    await navigate("next");
    const weekNumber = await queryFirst(`th .fc-timegrid-axis-cushion`).textContent;
    await getService("action").switchView("list");
    await getService("action").switchView("calendar");
    expect(`th .fc-timegrid-axis-cushion:eq(0)`).toHaveText(weekNumber);
});

test(`check if active fields are fetched in addition to field names in record data(search_read rpc)`, async () => {
    class CustomWidget extends Component {
        static template = xml``;
        static props = ["*"];
    }
    registry.category("fields").add("custom_widget", {
        component: CustomWidget,
        fieldDependencies: [{ name: "delay", type: "float" }],
    });

    onRpc("event", "search_read", ({ kwargs }) => {
        expect.step("event.search_read");
        expect(kwargs.fields).toInclude("delay");
    });

    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start">
                <field name="user_id" widget="custom_widget"/>
            </calendar>
        `,
    });

    expect.verifySteps(["event.search_read"]);
});

test("update time while drag and drop on month mode", async () => {
    patchWithCleanup(CalendarRenderer.prototype, {
        get actionSwiperProps() {
            const props = super.actionSwiperProps;
            props.onLeftSwipe = undefined;
            props.onRightSwipe = undefined;
            return props;
        },
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" mode="month" event_open_popup="1" quick_create="0">
                <field name="name"/>
                <field name="partner_id"/>
            </calendar>
        `,
    });

    await clickDate("2016-12-20");
    await contains(".modal-body .o_field_widget[name=name] input").edit("An event");
    await contains(".modal-body .o_field_widget[name=start] button").click();
    await contains(".modal-body .o_field_widget[name=start] input").edit("2016-12-20 08:00:00");
    await contains(".modal-body .o_field_widget[name=stop] button").click();
    await contains(".modal-body .o_field_widget[name=stop] input").edit("2016-12-23 10:00:00");
    await contains(".modal .o_form_button_save").click();
    await moveEventToDate(8, "2016-12-27");
    await clickEvent(8);
    await contains(".o_cw_popover_edit").click();

    expect(".o_field_widget[name='start']").toHaveText("Dec 26, 8:00 AM");
    expect(".o_field_widget[name='stop']").toHaveText("Dec 29, 10:00 AM");
});

test("html field on calendar shouldn't have a tooltip", async () => {
    Event._fields.description = fields.Html();
    Event._records[0].description = "<p>test html field</p>";
    await mountView({
        type: "calendar",
        resModel: "event",
        arch: `
            <calendar date_start="start">
                <field name="description"/>
            </calendar>
        `,
    });

    await clickEvent(MockServer.env["event"][0].id);
    const descriptionField = queryFirst('.o_cw_popover_field .o_field_widget[name="description"]');
    const parentLi = descriptionField.closest("li");
    expect(parentLi).toHaveAttribute("data-tooltip", "");
});

test.tags("mobile");
test("simple calendar rendering in mobile", async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar date_start="start" date_stop="stop"><field name="name"/></calendar>`,
    });

    expect(".o_calendar_button_prev").toHaveCount(0, { message: "prev button should be hidden" });
    expect(".o_calendar_button_next").toHaveCount(0, { message: "next button should be hidden" });
    expect(".o_calendar_container .o_calendar_header button.o_calendar_button_today").toBeVisible({
        message: "today button should be visible",
    });
    // Test all views
    // displays month mode by default
    expect(".o_calendar_container .o_calendar_header .dropdown-toggle").toHaveText("Week", {
        message: "should display the current week",
    });
    // switch to day mode
    await contains(".o_calendar_container .o_calendar_header .dropdown-toggle").click();
    await contains(".o-dropdown--menu .o_scale_button_day").click();
    await animationFrame();
    expect(".o_calendar_container .o_calendar_header .dropdown-toggle").toHaveText("Day", {
        message: "should display the current day",
    });
    // switch to month mode
    await contains(".o_calendar_container .o_calendar_header .dropdown-toggle").click();
    await contains(".o-dropdown--menu .o_scale_button_month").click();
    // await nextTick();
    expect(".o_calendar_container .o_calendar_header .dropdown-toggle").toHaveText("Month", {
        message: "should display the current month",
    });

    // switch to year mode
    await contains(".o_calendar_container .o_calendar_header .dropdown-toggle").click();
    await contains(".o-dropdown--menu .o_scale_button_year").click();
    // await nextTick();
    expect(".o_calendar_container .o_calendar_header .dropdown-toggle").toHaveText("Year", {
        message: "should display the current year",
    });
});

test.tags("mobile");
test("calendar: popover is rendered as dialog in mobile", async () => {
    // Legacy name of this test: "calendar: popover rendering in mobile"
    await mountView({
        type: "calendar",
        resModel: "event",
        arch: `<calendar date_start="start" date_stop="stop"><field name="name"/></calendar>`,
    });

    await clickEvent(1);
    expect(".o_cw_popover").toHaveCount(0);
    expect(".modal").toHaveCount(1);
    expect(".modal").toHaveClass("o_modal_full");

    expect(".modal-footer .btn").toHaveCount(2);
    expect(".modal-footer .btn.btn-primary.o_cw_popover_edit").toHaveCount(1);
    expect(".modal-footer .btn.btn-secondary.o_cw_popover_delete").toHaveCount(1);
});

test.tags("mobile");
test("calendar: today button", async () => {
    await mountView({
        type: "calendar",
        resModel: "event",
        arch: `<calendar mode="day" date_start="start" date_stop="stop"></calendar>`,
    });
    expandCalendarView();
    expect(queryFirst(".fc-col-header-cell[data-date]").dataset.date).toBe("2016-12-12");

    await navigate("prev");

    expect(queryFirst(".fc-col-header-cell[data-date]").dataset.date).toBe("2016-12-11");

    await contains(".o_calendar_button_today").click();
    expect(queryFirst(".fc-col-header-cell[data-date]").dataset.date).toBe("2016-12-12");
});

test.tags("mobile");
test("calendar: show and change other calendar", async () => {
    await mountView({
        type: "calendar",
        resModel: "event",
        arch: `
            <calendar date_start="start" date_stop="stop" color="partner_id">
                <filter name="user_id" avatar_field="image"/>
                <field name="partner_id" filters="1" invisible="1"/>
            </calendar>`,
    });

    expect(".o_calendar_renderer").toHaveCount(1);
    expect(".o_other_calendar_panel").toHaveCount(1);
    await displayCalendarPanel();
    expect(".o_calendar_filter_items_checkall").toHaveCount(1, {
        message: "should contain one filter to check all",
    });
    expect(".o_calendar_filter_item").toHaveCount(2, {
        message: "should contain 2 child nodes -> 2 resources",
    });

    expect(".o_calendar_sidebar").toHaveCount(1);
    expect(".o_calendar_renderer").toHaveCount(0);
    expect(".o_calendar_filter").toHaveCount(1);
    expect(".o_calendar_filter[data-name=partner_id]").toHaveCount(1);

    // Toggle the whole section filters by unchecking the all items checkbox
    await hideCalendarPanel();
    await toggleSectionFilter("partner_id");
    await displayCalendarPanel();
    expect(".o_other_calendar_panel .o_filter > *").toHaveCount(0, {
        message: "should contain 0 child nodes -> no filters selected",
    });

    // Toggle again the other calendar panel should hide the sidebar and show the calendar view
    await contains(".o_other_calendar_panel").click();
    expect(".o_calendar_sidebar").toHaveCount(0);
    expect(".o_calendar_renderer").toHaveCount(1);
});

test.tags("mobile");
test('calendar: tap on "Free Zone" opens quick create', async () => {
    patchWithCleanup(CalendarCommonRenderer.prototype, {
        onDateClick(...args) {
            expect.step("dateClick");
            return super.onDateClick(...args);
        },
        onSelect(...args) {
            expect.step("select");
            return super.onSelect(...args);
        },
    });

    await mountView({
        type: "calendar",
        resModel: "event",
        arch: `<calendar mode="day" date_start="start" date_stop="stop"/>`,
    });
    expandCalendarView();

    // Simulate a "TAP" (touch)
    await click(".fc-timegrid-slot-lane.fc-timegrid-slot-minor[data-time='08:30:00']");
    await animationFrame();

    // should open a Quick create modal view in mobile on short tap
    expect(".modal").toHaveCount(1);
    expect.verifySteps(["dateClick"]);
});

test.tags("mobile");
test('calendar: select range on "Free Zone" opens quick create', async () => {
    patchWithCleanup(CalendarCommonRenderer.prototype, {
        onDateClick(info) {
            expect.step("dateClick");
            return super.onDateClick(info);
        },
        onSelect(info) {
            expect.step("select");
            expect(info.startStr).toBe("2016-12-12T08:00:00+01:00");
            expect(info.endStr).toBe("2016-12-12T09:00:00+01:00");
            return super.onSelect(info);
        },
    });

    await mountView({
        type: "calendar",
        resModel: "event",
        arch: `<calendar mode="day" date_start="start" date_stop="stop"/>`,
    });
    expandCalendarView();

    await selectRange(
        ".fc-timegrid-slot-lane[data-time='08:00:00']",
        ".fc-timegrid-slot-lane[data-time='08:30:00']",
        { start: "top", end: "bottom" }
    );

    // should open a Quick create modal view in mobile on short tap
    expect(".modal").toHaveCount(1);
    expect.verifySteps(["select"]);
});

test("calendar (year): select date range opens quick create", async () => {
    patchWithCleanup(CalendarYearRenderer.prototype, {
        onDateClick(info) {
            expect.step("dateClick");
            return super.onDateClick(info);
        },
        onSelect(info) {
            expect.step("select");
            expect(info.startStr).toBe("2016-02-02");
            expect(info.endStr).toBe("2016-02-06"); // end date is exclusive
            return super.onSelect(info);
        },
    });

    await mountView({
        type: "calendar",
        resModel: "event",
        arch: `<calendar mode="year" date_start="start" date_stop="stop"/>`,
    });
    expandCalendarView();

    // Tap on a date
    await selectRange(
        ".fc-daygrid-day[data-date='2016-02-02']",
        ".fc-daygrid-day[data-date='2016-02-05']"
    );

    // should open a Quick create modal view in mobile on short tap
    expect(".modal").toHaveCount(1);
    expect.verifySteps(["select"]);
});

test.tags("mobile");
test("calendar (year): tap on date switch to day scale", async () => {
    await mountView({
        type: "calendar",
        resModel: "event",
        arch: `<calendar mode="year" date_start="start" date_stop="stop"/>`,
    });
    expandCalendarView();

    // Should display year view
    expect(".fc-dayGridYear-view").toHaveCount(1);
    expect(".fc-month-container").toHaveCount(12);

    // Tap on a date
    await click(".fc-daygrid-day[data-date='2016-02-05']");
    await animationFrame(); // switch renderer
    await animationFrame(); // await breadcrumb update
    expect(".o_calendar_container .o_calendar_header h5").toHaveText("5 February 2016");

    // Should display day view
    expect(".fc-dayGridYear-view").toHaveCount(0);
    expect(".fc-timeGridDay-view").toHaveCount(1);
    expect(queryFirst(".fc-col-header-cell[data-date]").dataset.date).toBe("2016-02-05");

    // Change scale to month
    await changeScale("month");
    expect(".o_calendar_container .o_calendar_header h5").toHaveCount(1);
    expect(".o_calendar_container .o_calendar_header h5").toHaveText("February 2016");
    expect(".fc-timeGridDay-view").toHaveCount(0);
    expect(".fc-dayGridMonth-view").toHaveCount(1);

    // Tap on a date
    await click(".fc-daygrid-day[data-date='2016-02-10']");
    await animationFrame(); // await reload & render
    await animationFrame(); // await breadcrumb update
    expect(".o_calendar_container .o_calendar_header h5").toHaveText("February 2016");

    // should open a Quick create modal view in mobile on short tap on date in monthly view
    expect(".modal").toHaveCount(1);
});

test("calendar: check context is correclty sent to fetch data", async () => {
    expect.assertions(1);
    onRpc("event", "search_read", ({ kwargs }) => {
        const { active_test } = kwargs.context;
        expect(active_test).toBe(true);
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop">
                <field name="name"/>
            </calendar>`,
        context: { active_test: true },
    });
});

test(`disable editing without write access rights`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" edit="0">
                <field name="name"/>
            </calendar>
        `,
    });
    expect(`.fc-event-draggable`).toHaveCount(0, {
        message: "Record should not be draggable/editable",
    });
});

test(`calendar view with show_unusual_days`, async () => {
    let unusualDays = {
        "2016-12-14": true,
    };
    onRpc("get_unusual_days", ({ args }) => {
        expect.step(`get_unusual_days from ${args[0]} to ${args[1]}`);
        return unusualDays;
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" show_unusual_days="1">
                <field name="name"/>
            </calendar>
        `,
    });
    expect(".fc-daygrid-day.o_calendar_disabled").toHaveCount(1);
    expect(".fc-daygrid-day.o_calendar_disabled").toHaveAttribute("data-date", "2016-12-14");

    unusualDays = {
        "2016-12-14": true,
        "2016-12-21": true,
    };
    await changeScale("month");
    expect(".fc-daygrid-day.o_calendar_disabled").toHaveCount(2);
    expect(".fc-daygrid-day.o_calendar_disabled:eq(0)").toHaveAttribute("data-date", "2016-12-14");
    expect(".fc-daygrid-day.o_calendar_disabled:eq(1)").toHaveAttribute("data-date", "2016-12-21");

    await changeScale("week");
    expect(".fc-daygrid-day.o_calendar_disabled").toHaveCount(1);
    expect(".fc-daygrid-day.o_calendar_disabled").toHaveAttribute("data-date", "2016-12-14");

    unusualDays = {};
    await navigate("next");
    expect(".fc-daygrid-day.o_calendar_disabled").toHaveCount(0);

    await navigate("prev");
    expect(".fc-daygrid-day.o_calendar_disabled").toHaveCount(1);
    expect(".fc-daygrid-day.o_calendar_disabled").toHaveAttribute("data-date", "2016-12-14");

    expect.verifySteps([
        "get_unusual_days from 2016-12-10 23:00:00 to 2016-12-17 22:59:59",
        "get_unusual_days from 2016-11-26 23:00:00 to 2017-01-07 22:59:59",
        "get_unusual_days from 2016-12-17 23:00:00 to 2016-12-24 22:59:59",
    ]);
});

test.tags("desktop");
test(`calendar renderer is rendered once after search refresh`, async () => {
    patchWithCleanup(CalendarRenderer.prototype, {
        setup() {
            super.setup();
            onRendered(() => expect.step("rendered"));
        },
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop">
                <filter name="user_id"/>
            </calendar>
        `,
    });
    expect.verifySteps(["rendered"]);
    await validateSearch();
    expect.verifySteps(["rendered"]);
});

test.tags("desktop");
test(`calendar with filters and count aggregate`, async () => {
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" aggregate="id:count">
                <field name="attendee_ids" write_model="filter.partner" write_field="partner_id" filter_field="is_checked"/>
            </calendar>
        `,
    });

    expect(queryAllTexts(".o_calendar_filter_item span")).toEqual(["partner 1", "2", "partner 2"]);
});

test.tags("desktop");
test(`calendar with dynamic filters and sum aggregate`, async () => {
    Event._fields.revenue = fields.Float();
    Event._records[0].revenue = 1200;
    Event._records[1].revenue = 350;
    Event._records[2].revenue = 800;
    Event._records[3].revenue = 3000;
    Event._records[4].revenue = 1900;
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `
            <calendar date_start="start" date_stop="stop" aggregate="revenue:sum">
                <field name="partner_id" filters="1"/>
            </calendar>
        `,
    });

    expect(queryAllTexts(".o_calendar_filter_item span")).toEqual([
        "partner 1",
        "4,550",
        "partner 4",
        "2,700",
    ]);
});

test.tags("desktop");
test(`Hour format mirror event`, async () => {
    onRpc("create", ({ args }) => {
        expect.step("create");
    });
    await mountView({
        resModel: "event",
        type: "calendar",
        arch: `<calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="is_all_day" mode="year"/>`,
    });

    await changeScale("week");

    await selectTimeRange("2016-12-13 11:00:00", "2016-12-13 16:30:00");
    // Verify highlighted event
    expect(`.fc-event-mirror`).toHaveText("11:00 - 16:30");
    await contains(`.o-calendar-quick-create--input`).edit("mirror_event", { confirm: false });
    await contains(`.o-calendar-quick-create--create-btn`).click();

    expect.verifySteps(["create"]);

    expect(`.o_event[data-event-id="8"] .fc-event-main .o_event_title`).toHaveText("mirror_event");
    expect(`.o_event[data-event-id="8"] .fc-event-main .fc-time`).toHaveText("11:00");
});
