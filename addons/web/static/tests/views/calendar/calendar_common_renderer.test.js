// @ts-check

import { beforeEach, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    queryAll,
    queryAllTexts,
    queryFirst,
    queryRect,
} from "@odoo/hoot-dom";
import { mockDate, runAllTimers } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    mockService,
    mountWithCleanup,
    preloadFullCalendar,
} from "@web/../tests/web_test_helpers";
import { CallbackRecorder } from "@web/core/action_hook";
import { luxon } from "@web/core/l10n/luxon";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";

import {
    clickAllDaySlot,
    clickEvent,
    DEFAULT_DATE,
    FAKE_MODEL,
    findEvent,
    selectTimeRange,
} from "./calendar_test_helpers.js";

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
    return await mountWithCleanup(CalendarCommonRenderer, {
        props: { ...FAKE_PROPS, ...props },
        target,
    });
}

preloadFullCalendar();
beforeEach(() => {
    luxon.Settings.defaultZone = "Africa/Algiers";
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
    expect(`.fc-week-number`).toHaveCount(1);
    expect(`.fc-week-number`).toHaveText(/(Week )?28/);
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
            expect(record.start.valueOf()).toBe(
                luxon.DateTime.local(2021, 7, 16, 8, 0).valueOf(),
            );
            expect(record.end.valueOf()).toBe(
                luxon.DateTime.local(2021, 7, 16, 10, 0).valueOf(),
            );
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
    mockService("popover", {
        add(target, component, { record }) {
            expect.step("popover");
            expect(record.id).toBe(1);
            return async () => {};
        },
    });
    await start({ model: { ...FAKE_MODEL, scale: "day" } });
    await clickEvent(1);
    await runAllTimers();
    expect.verifySteps(["popover"]);
});

test.tags("desktop");
test(`two fast single-clicks on DIFFERENT events open both popovers, no edit`, async () => {
    mockService("popover", {
        add(target, component, { record }) {
            expect.step(`popover-${record.id}`);
            return async () => {};
        },
    });
    await start({
        editRecord(record) {
            expect.step(`edit-${record.id}`);
        },
    });
    await click(findEvent(1));
    await click(findEvent(2));
    await runAllTimers();
    expect.verifySteps(["popover-1", "popover-2"]);
});

test.tags("desktop");
test(`two fast clicks on the SAME event still open the edit form`, async () => {
    mockService("popover", {
        add() {
            expect.step("popover");
            return async () => {};
        },
    });
    await start({
        editRecord(record) {
            expect.step(`edit-${record.id}`);
        },
    });
    await click(findEvent(1));
    await click(findEvent(1));
    await runAllTimers();
    expect.verifySteps(["edit-1"]);
});

test(`Week: check week number`, async () => {
    await start({ model: { ...FAKE_MODEL, scale: "week" } });
    expect(`.fc-week-number`).toHaveCount(1);
    expect(`.fc-week-number`).toHaveText(/(Week )?28/);
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
    await animationFrame();
    const scrollerY = queryRect(`.fc-scroller-liquid-y`).y;
    const slotY = queryRect(`[data-time="06:00:00"]:eq(0)`).y;
    expect(Math.abs(slotY - scrollerY)).toBeLessThan(2);
});

test(`Week: automatically scroll to 6am`, async () => {
    await mountWithCleanup(`<div class="scrollable" style="height: 500px;"/>`);
    await start({ model: { ...FAKE_MODEL, scale: "week" } }, queryFirst(`.scrollable`));
    await runAllTimers();
    await animationFrame();
    const scrollerY = queryRect(`.fc-scroller-liquid-y`).y;
    const slotY = queryRect(`[data-time="06:00:00"]:eq(0)`).y;
    expect(Math.abs(slotY - scrollerY)).toBeLessThan(2);
});

test("Month: remove row when no day of current month", async () => {
    await start({ model: { ...FAKE_MODEL, scale: "month" } });
    expect(".fc-day-other, .fc-day-disabled").toHaveCount(4);
});

test(`o_past_event: an all-day event on its last day today is not styled past`, async () => {
    mockDate("2021-07-16T12:00:00");
    const today = luxon.DateTime.now().startOf("day");
    const model = {
        ...FAKE_MODEL,
        records: {
            10: {
                id: 10,
                title: "all day today",
                isAllDay: true,
                start: today,
                end: today,
            },
            11: {
                id: 11,
                title: "all day yesterday",
                isAllDay: true,
                start: today.minus({ days: 1 }),
                end: today.minus({ days: 1 }),
            },
            12: {
                id: 12,
                title: "timed, already ended today",
                isAllDay: false,
                start: today.plus({ hours: 8 }),
                end: today.plus({ hours: 9 }),
            },
        },
    };
    const renderer = await start({ model });
    expect(renderer.eventClassNames({ event: { id: 10 } })).not.toInclude(
        "o_past_event",
    );
    expect(renderer.eventClassNames({ event: { id: 11 } })).toInclude("o_past_event");
    expect(renderer.eventClassNames({ event: { id: 12 } })).toInclude("o_past_event");
});

test(`isSelectionAllowed: a timed selection ending exactly at midnight is allowed`, async () => {
    const renderer = await start();
    // the instants must be built in luxon's default zone, the one fromFcDate
    // reads them in: a native Date built with setHours() lives in the browser's
    // real zone, and the assertion then depends on where the test runs
    const atLocal = (year, month, day, hour) =>
        luxon.DateTime.fromObject({ year, month, day, hour }).toJSDate();
    expect(
        renderer.isSelectionAllowed({
            allDay: false,
            start: atLocal(2021, 7, 16, 23),
            end: atLocal(2021, 7, 17, 0),
        }),
    ).toBe(true);
    expect(
        renderer.isSelectionAllowed({
            allDay: false,
            start: atLocal(2021, 7, 16, 8),
            end: atLocal(2021, 7, 16, 9),
        }),
    ).toBe(true);
    expect(
        renderer.isSelectionAllowed({
            allDay: false,
            start: atLocal(2021, 7, 16, 22),
            end: atLocal(2021, 7, 17, 1),
        }),
    ).toBe(false);
});

test(`fcEventToRecord returns null when the dragged record was removed mid-interaction`, async () => {
    const renderer = await start({ model: { ...FAKE_MODEL, scale: "week" } });
    expect(
        renderer.fcEventToRecord({
            id: 9999,
            allDay: false,
            start: new Date(2021, 6, 16, 10, 0),
            end: new Date(2021, 6, 16, 11, 0),
        }),
    ).toBe(null);
    expect(
        renderer.fcEventToRecord({
            id: 1,
            allDay: false,
            start: new Date(2021, 6, 16, 10, 0),
            end: new Date(2021, 6, 16, 11, 0),
        }).id,
    ).toBe(1);
});

test(`onEventDrop no-ops (and reverts) when the record vanished mid-drag`, async () => {
    let updated = false;
    let reverted = false;
    const renderer = await start({
        model: {
            ...FAKE_MODEL,
            scale: "week",
            updateRecord: () => {
                updated = true;
            },
        },
    });
    renderer.onEventDrop({
        event: {
            id: 9999,
            allDay: false,
            start: new Date(2021, 6, 16, 10, 0),
            end: new Date(2021, 6, 16, 11, 0),
        },
        revert: () => {
            reverted = true;
        },
    });
    expect(updated).toBe(false);
    expect(reverted).toBe(true);
});

test(`eventSources: a source other than the records refetches the events when it changes`, async () => {
    let mapped = 0;
    class SlotRenderer extends CalendarCommonRenderer {
        eventSources() {
            return [...super.eventSources(), this.props.model.slots];
        }
        mapRecordsToEvents() {
            mapped++;
            return [
                ...super.mapRecordsToEvents(),
                ...Object.values(this.props.model.slots).map((slot) =>
                    this.convertRecordToEvent(slot),
                ),
            ];
        }
    }
    class Parent extends Component {
        static components = { SlotRenderer };
        static template = xml`<SlotRenderer t-props="this.state.props"/>`;
        static props = {};
        setup() {
            this.state = useState({
                props: { ...FAKE_PROPS, model: { ...FAKE_MODEL, slots: {} } },
            });
        }
    }
    const parent = await mountWithCleanup(Parent);
    const shown = queryAll(".fc-event").length;
    expect(shown).toBeGreaterThan(0);
    expect(mapped).toBe(1, { message: "mounting fetches the events once" });

    const model = parent.state.props.model;
    parent.state.props = { ...parent.state.props, model: { ...model } };
    await animationFrame();
    expect(mapped).toBe(1, {
        message: "a render whose sources are the same objects does not refetch",
    });

    const slot = {
        id: 100,
        title: "a slot",
        start: DEFAULT_DATE.plus({ days: 1 }),
        end: DEFAULT_DATE.plus({ days: 1 }),
        isAllDay: true,
    };
    parent.state.props = {
        ...parent.state.props,
        model: { ...model, slots: { 100: slot } },
    };
    await animationFrame();
    expect(mapped).toBe(2, { message: "a new slots object is a changed source" });
    expect(".fc-event").toHaveCount(shown + 1);
    expect(findEvent(100)).toHaveText(/a slot/);
});
