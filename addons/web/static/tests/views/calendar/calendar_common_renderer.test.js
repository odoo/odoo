import { beforeEach, expect, test } from "@odoo/hoot";
import { queryAllTexts, queryFirst, queryRect } from "@odoo/hoot-dom";
import { runAllTimers } from "@odoo/hoot-mock";
import { mockService, mountWithCleanup, preloadBundle } from "@web/../tests/web_test_helpers";
import {
    DEFAULT_DATE,
    FAKE_MODEL,
    clickAllDaySlot,
    clickEvent,
    selectTimeRange,
} from "./calendar_test_helpers";

import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CallbackRecorder } from "@web/search/action_hook";

const FAKE_PROPS = {
    model: FAKE_MODEL,
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
    expect(`.o_calendar_widget.fc`).toHaveCount(1);
});

test(`Day: mount a CalendarCommonRenderer`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "day" } });
    expect(`.o_calendar_widget.fc .fc-timeGridDay-view`).toHaveCount(1);
});

test(`Week: mount a CalendarCommonRenderer`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "week" } });
    expect(`.o_calendar_widget.fc .fc-timeGridWeek-view`).toHaveCount(1);
});

test(`Month: mount a CalendarCommonRenderer`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "month" } });
    expect(`.o_calendar_widget.fc .fc-dayGridMonth-view`).toHaveCount(1);
});

test(`Day: check week number`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "day" } });
    expect(`[aria-label^="Week "]`).toHaveCount(1);
    expect(`[aria-label^="Week "]`).toHaveText(/(Week )?28/);
});

test(`Day: check date`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "day" } });
    expect(`.fc-col-header-cell.fc-day`).toHaveCount(1);
    expect(`.fc-col-header-cell.fc-day:eq(0) .o_cw_day_name`).toHaveText("Friday");
    expect(`.fc-col-header-cell.fc-day:eq(0) .o_cw_day_number`).toHaveText("16");
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
    expect(`.fc-scrollgrid-section-header .fc-timegrid-axis-cushion`).toHaveCount(1);
    expect(`.fc-scrollgrid-section-header .fc-timegrid-axis-cushion`).toHaveText(/(Week )?28/);
});

test(`Week: check dates`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "week" } });
    expect(`.fc-col-header-cell.fc-day`).toHaveCount(7);
    expect(queryAllTexts(`.fc-col-header-cell .o_cw_day_name`)).toEqual([
        "Sun",
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
    ]);
    expect(queryAllTexts`.fc-col-header-cell .o_cw_day_number`).toEqual([
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
    ]);
});

test(`Day: automatically scroll to 6am`, async () => {
    await mountWithCleanup(`<div class="scrollable" style="height: 500px;"/>`);
    await start({ model: { ...FAKE_MODEL, scale: "day" } }, queryFirst(`.scrollable`));

    const containerDimensions = queryRect(`.fc-scrollgrid-section-liquid .fc-scroller`);
    const dayStartDimensions = queryRect(`.fc-timegrid-slot[data-time="06:00:00"]:eq(0)`);
    expect(Math.abs(dayStartDimensions.y - containerDimensions.y)).toBeLessThan(2);
});

test(`Week: automatically scroll to 6am`, async () => {
    await mountWithCleanup(`<div class="scrollable" style="height: 500px;"/>`);
    await start({ model: { ...FAKE_MODEL, scale: "week" } }, queryFirst(`.scrollable`));

    const containerDimensions = queryRect(`.fc-scrollgrid-section-liquid .fc-scroller`);
    const dayStartDimensions = queryRect(`.fc-timegrid-slot[data-time="06:00:00"]:eq(0)`);
    expect(Math.abs(dayStartDimensions.y - containerDimensions.y)).toBeLessThan(2);
});

test("Month: remove row when no day of current month", async () => {
    await start({ model: { ...FAKE_MODEL, scale: "month" } });
    expect(".fc-day-other, .fc-day-disabled").toHaveCount(4);
});
