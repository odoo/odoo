import { beforeEach, expect, test } from "@odoo/hoot";
import { queryAllTexts, queryFirst, queryRect } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers, mockTimeZone } from "@odoo/hoot-mock";
import { mockService, mountWithCleanup, preloadBundle } from "@web/../tests/web_test_helpers";
import {
    DEFAULT_DATE,
    FAKE_MODEL,
    clickAllDaySlot,
    clickEvent,
    findTimeGridScroller,
    selectTimeRange,
} from "./calendar_test_helpers";

import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CallbackRecorder } from "@web/search/action_hook";

const FAKE_PROPS = {
    model: FAKE_MODEL,
    initialDate: FAKE_MODEL.date,
    createRecord() {},
    deleteRecord() {},
    editRecord() {},
    callbackRecorder: new CallbackRecorder(),
    onSquareSelection() {},
    cleanSquareSelection() {},
};

async function start(props = {}, target) {
    await mountWithCleanup(CalendarCommonRenderer, {
        props: { ...FAKE_PROPS, ...props },
        target,
    });
}

preloadBundle("web.fullcalendar_lib");
beforeEach(() => {
    luxon.Settings.defaultZone = "UTC+1";
});

test(`mount a CalendarCommonRenderer`, async () => {
    await start();
    expect(`.o_calendar_widget .o_calendar_fc_view`).toHaveCount(1);
});

test(`Day: mount a CalendarCommonRenderer`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "day" } });
    expect(`.o_calendar_widget .o_calendar_fc_view_timeGridDay`).toHaveCount(1);
});

test(`Week: mount a CalendarCommonRenderer`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "week" } });
    expect(`.o_calendar_widget .o_calendar_fc_view_timeGridWeek`).toHaveCount(1);
});

test(`Month: mount a CalendarCommonRenderer`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "month" } });
    expect(`.o_calendar_widget .o_calendar_fc_view_dayGridMonth`).toHaveCount(1);
});

test(`Day: check week number`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "day" } });
    expect(`.o_calendar_week_number_header`).toHaveCount(1);
    expect(`.o_calendar_week_number_header`).toHaveText(/(Week )?28/);
});

test(`Day: check date`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "day" } });
    expect(`.o_calendar_header_cell`).toHaveCount(1);
    expect(`.o_calendar_header_cell:eq(0) .o_calendar_day_name`).toHaveText("Friday");
    expect(`.o_calendar_header_cell:eq(0) .o_calendar_day_number`).toHaveText("16");
});

test(`Day: click all day slot`, async () => {
    await start({
        model: { ...FAKE_MODEL, scale: "day" },
        createRecord(record) {
            expect.step("create");
            expect(record.isAllDay).toBe(true);
            expect(record.start.valueOf()).toBe(DEFAULT_DATE.startOf("day").valueOf());
        },
    });
    await clickAllDaySlot("2021-07-16");
    expect.verifySteps(["create"]);
});

test.tags("desktop");
test(`Day: select range`, async () => {
    await start({
        model: { ...FAKE_MODEL, scale: "day" },
        createRecord(record) {
            expect.step("create");
            expect(record.isAllDay).toBe(false);
            expect(record.start.valueOf()).toBe(luxon.DateTime.local(2021, 7, 16, 8, 0).valueOf());
            expect(record.end.valueOf()).toBe(luxon.DateTime.local(2021, 7, 16, 10, 0).valueOf());
        },
    });
    await selectTimeRange("2021-07-16 08:00:00", "2021-07-16 10:00:00");
    expect.verifySteps(["create"]);
});

test(`Day: check event`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "day" } });
    expect(`.o_event`).toHaveCount(1);
    expect(`.o_event`).toHaveAttribute("data-event-id", "1");
});

test.tags("desktop");
test(`Day: click on event`, async () => {
    mockService("popover", () => ({
        add(target, component, { record }) {
            expect.step("popover");
            expect(record.id).toBe(1);
            return () => {};
        },
    }));
    await start({ model: { ...FAKE_MODEL, scale: "day" } });
    await clickEvent(1);
    await runAllTimers();
    expect.verifySteps(["popover"]);
});

test(`Week: check week number`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "week" } });
    expect(`.o_calendar_week_number_header`).toHaveCount(1);
    expect(`.o_calendar_week_number_header`).toHaveText(/(Week )?28/);
});

test(`Week: check dates`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "week" } });
    expect(`.o_calendar_header_cell`).toHaveCount(7);
    expect(queryAllTexts(`.o_calendar_header_cell .o_calendar_day_name`)).toEqual([
        "SUN",
        "MON",
        "TUE",
        "WED",
        "THU",
        "FRI",
        "SAT",
    ]);
    expect(queryAllTexts`.o_calendar_header_cell .o_calendar_day_number`).toEqual([
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
    ]);
});

test("Week: check dates across a DST transition happening at local midnight (Africa/Cairo)", async () => {
    // Egypt springs its clock forward from 00:00 to 01:00 on the last Friday of
    // April, so "midnight" doesn't exist as a local time that day. This used to
    // make FullCalendar's Luxon timezone plugin resolve that day's header to the
    // previous day (duplicating its weekday name).
    mockTimeZone("Africa/Cairo");

    await start({
        model: {
            ...FAKE_MODEL,
            scale: "week",
        },
        initialDate: luxon.DateTime.local(2027, 4, 25),
    });

    expect(`.o_calendar_header_cell`).toHaveCount(7);
    expect(queryAllTexts(`.o_calendar_header_cell .o_calendar_day_name`)).toEqual([
        "SUN",
        "MON",
        "TUE",
        "WED",
        "THU",
        "FRI",
        "SAT",
    ]);
    expect(queryAllTexts`.o_calendar_header_cell .o_calendar_day_number`).toEqual([
        "25",
        "26",
        "27",
        "28",
        "29",
        "30",
        "1",
    ]);
});

test(`Day: automatically scroll to 6am`, async () => {
    await mountWithCleanup(`<div class="scrollable" style="height: 500px;"/>`);
    await start({ model: { ...FAKE_MODEL, scale: "day" } }, queryFirst(`.scrollable`));
    await animationFrame();

    const containerDimensions = findTimeGridScroller().getBoundingClientRect();
    const dayStartDimensions = queryRect(`.o_calendar_time_slot_label[data-time="06:00:00"]`);
    // the time grid has a 15px gap on top to show the first time label
    expect(Math.abs(dayStartDimensions.y - containerDimensions.y - 15)).toBeLessThan(2);
});

test(`Week: automatically scroll to 6am`, async () => {
    await mountWithCleanup(`<div class="scrollable" style="height: 500px;"/>`);
    await start({ model: { ...FAKE_MODEL, scale: "week" } }, queryFirst(`.scrollable`));
    await animationFrame();

    const containerDimensions = findTimeGridScroller().getBoundingClientRect();
    const dayStartDimensions = queryRect(`.o_calendar_time_slot_label[data-time="06:00:00"]`);
    // the time grid has a 15px gap on top to show the first time label
    expect(Math.abs(dayStartDimensions.y - containerDimensions.y - 15)).toBeLessThan(2);
});

test("Month: remove row when no day of current month", async () => {
    await start({ model: { ...FAKE_MODEL, scale: "month" } });
    expect(".o_calendar_day_other, [aria-disabled]").toHaveCount(4);
});
