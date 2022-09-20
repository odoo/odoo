/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { getFixture, patchWithCleanup } from "../../helpers/utils";
import {
    makeEnv,
    makeFakeModel,
    mountComponent,
    clickAllDaySlot,
    selectTimeRange,
    clickEvent,
    makeFakeDate,
} from "./helpers";

let target;

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
        displayName: "Plop",
        ...props,
    });
}

QUnit.module("CalendarView - CommonRenderer", ({ beforeEach }) => {
    beforeEach(() => {
        target = getFixture();
    });

    QUnit.test("mount a CalendarCommonRenderer", async (assert) => {
        await start({});
        assert.containsOnce(target, ".o_calendar_widget.fc");
    });

    QUnit.test("Day: mount a CalendarCommonRenderer", async (assert) => {
        await start({ model: { scale: "day" } });
        assert.containsOnce(target, ".o_calendar_widget.fc .fc-timeGridDay-view");
    });

    QUnit.test("Week: mount a CalendarCommonRenderer", async (assert) => {
        await start({ model: { scale: "week" } });
        assert.containsOnce(target, ".o_calendar_widget.fc .fc-timeGridWeek-view");
    });

    QUnit.test("Month: mount a CalendarCommonRenderer", async (assert) => {
        await start({ model: { scale: "month" } });
        assert.containsOnce(target, ".o_calendar_widget.fc .fc-dayGridMonth-view");
    });

    QUnit.test("Day: check week number", async (assert) => {
        await start({ model: { scale: "day" } });
        assert.containsOnce(target, ".fc-week-number");
        assert.strictEqual(target.querySelector(".fc-week-number").textContent, "Week 28");
    });

    QUnit.test("Day: check date", async (assert) => {
        await start({ model: { scale: "day" } });
        assert.containsOnce(target, ".fc-day-header");
        assert.strictEqual(target.querySelector(".fc-day-header").textContent, "July 16, 2021");
    });

    QUnit.test("Day: click all day slot", async (assert) => {
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout() {},
        });

        await start({
            model: { scale: "day" },
            props: {
                createRecord(record) {
                    const date = makeFakeDate().startOf("day");
                    assert.ok(record.isAllDay);
                    assert.strictEqual(record.start.valueOf(), date.valueOf());
                    assert.strictEqual(record.end.valueOf(), date.plus({ days: 1 }).valueOf());
                    assert.step("create");
                },
            },
        });

        await clickAllDaySlot(target, "2021-07-16");
        assert.verifySteps(["create"]);
    });

    QUnit.test("Day: select range", async (assert) => {
        await start({
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

        await selectTimeRange(target, "2021-07-16 00:30:00", "2021-07-16 02:30:00");
        assert.verifySteps(["create"]);
    });

    QUnit.test("Day: check event", async (assert) => {
        await start({ model: { scale: "day" } });
        assert.containsOnce(target, ".o_event");
        assert.hasAttrValue(target.querySelector(".o_event"), "data-event-id", "1");
    });

    QUnit.test("Day: click on event", async (assert) => {
        assert.expect(1);

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout() {},
        });

        await start({
            model: { scale: "day" },
            services: {
                popover: makeFakePopoverService((target, _, props) => {
                    assert.strictEqual(props.record.id, 1);
                    return () => {};
                }),
            },
        });

        await clickEvent(target, 1);
    });

    QUnit.test("Week: check week number", async (assert) => {
        await start({ model: { scale: "week" } });
        assert.containsOnce(target, ".fc-week-number");
        assert.strictEqual(target.querySelector(".fc-week-number").textContent, "Week 28");
    });

    QUnit.test("Week: check dates", async (assert) => {
        await start({ model: { scale: "week" } });
        assert.containsN(target, ".fc-day-header", 7);

        const dates = ["Sun 11", "Mon 12", "Tue 13", "Wed 14", "Thu 15", "Fri 16", "Sat 17"];

        const els = target.querySelectorAll(".fc-day-header");
        for (let i = 0; i < els.length; i++) {
            assert.strictEqual(els[i].textContent, dates[i]);
        }
    });
});
