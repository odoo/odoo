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
        const dayHeader = target.querySelector(".fc-day-header");
        assert.strictEqual(dayHeader.querySelector(".o_cw_day_name").textContent, "Friday");
        assert.strictEqual(dayHeader.querySelector(".o_cw_day_number").textContent, "16");
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
                    assert.notOk(record.isAllDay);
                    assert.strictEqual(
                        record.start.valueOf(),
                        luxon.DateTime.local(2021, 7, 16, 8, 0).valueOf()
                    );
                    assert.strictEqual(
                        record.end.valueOf(),
                        luxon.DateTime.local(2021, 7, 16, 10, 0).valueOf()
                    );
                    assert.step("create");
                },
            },
        });

        await selectTimeRange(target, "2021-07-16 08:00:00", "2021-07-16 10:00:00");
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

        const dateNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
        const dates = ["11", "12", "13", "14", "15", "16", "17"];

        const els = target.querySelectorAll(".fc-day-header");
        for (let i = 0; i < els.length; i++) {
            assert.strictEqual(els[i].querySelector(".o_cw_day_name").textContent, dateNames[i]);
            assert.strictEqual(els[i].querySelector(".o_cw_day_number").textContent, dates[i]);
        }
    });

    QUnit.test("Day: automatically scroll to 6am", async (assert) => {
        // Make calendar scrollable
        target.style.height = "500px";
        await start({ model: { scale: "day" } });
        const containerDimensions = target.querySelector(".fc-scroller").getBoundingClientRect();
        const dayStartDimensions = target
            .querySelector('tr[data-time="06:00:00"')
            .getBoundingClientRect();
        assert.ok(Math.abs(dayStartDimensions.y - containerDimensions.y) <= 2);
    });

    QUnit.test("Week: automatically scroll to 6am", async (assert) => {
        // Make calendar scrollable
        target.style.height = "500px";
        await start({ model: { scale: "week" } });
        const containerDimensions = target.querySelector(".fc-scroller").getBoundingClientRect();
        const dayStartDimensions = target
            .querySelector('tr[data-time="06:00:00"')
            .getBoundingClientRect();
        assert.ok(Math.abs(dayStartDimensions.y - containerDimensions.y) <= 2);
    });
});
