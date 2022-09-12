/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { patchWithCleanup } from "../../helpers/utils";
import {
    FAKE_DATE,
    makeEnv,
    makeFakeModel,
    mountComponent,
    clickAllDaySlot,
    selectTimeRange,
    clickEvent,
} from "./calendar_helpers";

function makeFakePopoverService(add) {
    return { start: () => ({ add }) };
}

async function start(params = {}) {
    const { services, props, model: modelParams } = params;
    const env = await makeEnv(services);
    const model = makeFakeModel(modelParams);
    return await mountComponent(CalendarCommonRenderer, env, {
        model,
        createRecord() {},
        deleteRecord() {},
        editRecord() {},
        ...props,
    });
}

QUnit.module("CalendarCommonRenderer");

QUnit.skipWOWL("mount a CalendarCommonRenderer", async (assert) => {
    const calendar = await start({});
    assert.containsOnce(calendar.el, ".o-calendar-common-renderer.fc");
});

QUnit.skipWOWL("Day: mount a CalendarCommonRenderer", async (assert) => {
    const calendar = await start({ model: { scale: "day" } });
    assert.containsOnce(calendar.el, ".o-calendar-common-renderer.fc .fc-timeGridDay-view");
});

QUnit.skipWOWL("Week: mount a CalendarCommonRenderer", async (assert) => {
    const calendar = await start({ model: { scale: "week" } });
    assert.containsOnce(calendar.el, ".o-calendar-common-renderer.fc .fc-timeGridWeek-view");
});

QUnit.skipWOWL("Month: mount a CalendarCommonRenderer", async (assert) => {
    const calendar = await start({ model: { scale: "month" } });
    assert.containsOnce(calendar.el, ".o-calendar-common-renderer.fc .fc-dayGridMonth-view");
});

QUnit.skipWOWL("Day: check week number", async (assert) => {
    const calendar = await start({ model: { scale: "day" } });
    assert.containsOnce(calendar.el, ".fc-week-number");
    assert.strictEqual(calendar.el.querySelector(".fc-week-number").textContent, "Week 28");
});

QUnit.skipWOWL("Day: check date", async (assert) => {
    const calendar = await start({ model: { scale: "day" } });
    assert.containsOnce(calendar.el, ".fc-day-header");
    assert.strictEqual(calendar.el.querySelector(".fc-day-header").textContent, "July 16, 2021");
});

QUnit.skipWOWL("Day: click all day slot", async (assert) => {
    patchWithCleanup(browser, {
        setTimeout: (fn) => fn(),
        clearTimeout() {},
    });

    const calendar = await start({
        model: { scale: "day" },
        props: {
            createRecord(record) {
                const date = FAKE_DATE.startOf("day");
                assert.ok(record.isAllDay);
                assert.strictEqual(record.start.valueOf(), date.valueOf());
                assert.strictEqual(record.end.valueOf(), date.plus({ days: 1 }).valueOf());
                assert.step("create");
            },
        },
    });

    await clickAllDaySlot(calendar, "2021-07-16");
    assert.verifySteps(["create"]);
});

QUnit.skipWOWL("Day: select range", async (assert) => {
    const calendar = await start({
        model: { scale: "day" },
        props: {
            createRecord(record) {
                const offset = luxon.DateTime.local().offset;
                assert.notOk(record.isAllDay);
                assert.strictEqual(
                    record.start.plus({ minutes: offset }).valueOf(),
                    luxon.DateTime.utc(2021, 7, 16, 0, 30).valueOf()
                );
                assert.strictEqual(
                    record.end.plus({ minutes: offset }).valueOf(),
                    luxon.DateTime.utc(2021, 7, 16, 2, 30).valueOf()
                );
                assert.step("create");
            },
        },
    });

    await selectTimeRange(calendar, "2021-07-16 00:30:00", "2021-07-16 02:30:00");
    assert.verifySteps(["create"]);
});

QUnit.skipWOWL("Day: check event", async (assert) => {
    const calendar = await start({ model: { scale: "day" } });
    assert.containsOnce(calendar.el, ".o_event");
    assert.hasAttrValue(calendar.el.querySelector(".o_event"), "data-event-id", "1");
});

QUnit.skipWOWL("Day: hover event", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "day" } });
});

QUnit.skipWOWL("Day: click on event", async (assert) => {
    patchWithCleanup(browser, {
        setTimeout: (fn) => fn(),
        clearTimeout() {},
    });

    const calendar = await start({
        model: { scale: "day" },
        services: {
            popover: makeFakePopoverService((target, _, props) => {
                assert.strictEqual(props.record.id, 1);
                return () => {};
            }),
        },
    });

    await clickEvent(calendar, 1);
});

QUnit.skipWOWL("Day: move event from all day slot to timed slot", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "day" } });
});

QUnit.skipWOWL("Day: move event from timed slot to timed slot", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "day" } });
});

QUnit.skipWOWL("Day: move event from timed slot to all day slot", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "day" } });
});

QUnit.skipWOWL("Day: resize event, increase time", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "day" } });
});

QUnit.skipWOWL("Day: resize event, decrease time", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "day" } });
});

QUnit.skipWOWL("Week: check week number", async (assert) => {
    const calendar = await start({ model: { scale: "week" } });
    assert.containsOnce(calendar.el, ".fc-week-number");
    assert.strictEqual(calendar.el.querySelector(".fc-week-number").textContent, "Week 28");
});

QUnit.skipWOWL("Week: check dates", async (assert) => {
    const calendar = await start({ model: { scale: "week" } });
    assert.containsN(calendar.el, ".fc-day-header", 7);

    const dates = [
        "July 11, 2021",
        "July 12, 2021",
        "July 13, 2021",
        "July 14, 2021",
        "July 15, 2021",
        "July 16, 2021",
        "July 17, 2021",
    ];

    const els = calendar.el.querySelectorAll(".fc-day-header");
    for (let i = 0; i < els.length; i++) {
        assert.strictEqual(els[i].textContent, dates[i]);
    }
});

QUnit.skipWOWL("Week: click all day slot", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "week" } });
});

QUnit.skipWOWL("Week: select range on same day", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "week" } });
});

QUnit.skipWOWL("Week: select range on different day", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "week" } });
});

QUnit.skipWOWL("Week: check event", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "week" } });
});

QUnit.skipWOWL("Week: hover event", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "week" } });
});

QUnit.skipWOWL("Week: click on event", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "week" } });
});

QUnit.skipWOWL("Week: move event from all day slot to timed slot on same day", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "week" } });
});

QUnit.skipWOWL("Week: move event from timed slot to timed slot on same day", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "week" } });
});

QUnit.skipWOWL("Week: move event from timed slot to all day slot on same day", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "week" } });
});

QUnit.skipWOWL(
    "Week: move event from all day slot to timed slot on different day",
    async (assert) => {
        assert.ok(false);
        // const calendar = await start({ model: { scale: "week" } });
    }
);

QUnit.skipWOWL(
    "Week: move event from timed slot to timed slot on different day",
    async (assert) => {
        assert.ok(false);
        // const calendar = await start({ model: { scale: "week" } });
    }
);

QUnit.skipWOWL(
    "Week: move event from timed slot to all day slot on different day",
    async (assert) => {
        assert.ok(false);
        // const calendar = await start({ model: { scale: "week" } });
    }
);

QUnit.skipWOWL("Week: resize event, increase time on same day", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "week" } });
});

QUnit.skipWOWL("Week: resize event, decrease time on same day", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "week" } });
});

QUnit.skipWOWL("Week: resize event, increase time on different day", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "week" } });
});

QUnit.skipWOWL("Week: resize event, decrease time on different day", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "week" } });
});

QUnit.skipWOWL("Month: check week numbers", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "month" } });
});

QUnit.skipWOWL("Month: check dates", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "month" } });
});

QUnit.skipWOWL("Month: click date", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "month" } });
});

QUnit.skipWOWL("Month: select range", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "month" } });
});

QUnit.skipWOWL("Month: check event", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "month" } });
});

QUnit.skipWOWL("Month: hover event", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "month" } });
});

QUnit.skipWOWL("Month: click on event", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "month" } });
});

QUnit.skipWOWL("Month: move event", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "month" } });
});

QUnit.skipWOWL("Month: resize event, increase time", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "month" } });
});

QUnit.skipWOWL("Month: resize event, decrease time", async (assert) => {
    assert.ok(false);
    // const calendar = await start({ model: { scale: "month" } });
});
