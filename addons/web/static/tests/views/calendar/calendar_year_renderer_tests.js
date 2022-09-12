/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";
import { nextTick, patchWithCleanup } from "../../helpers/utils";
import {
    clickDate,
    mountComponent,
    selectDateRange,
    makeEnv,
    makeFakeModel,
} from "./calendar_helpers";

function makeFakePopoverService(add) {
    return { start: () => ({ add }) };
}

async function start(params = {}) {
    const { services, props, model: modelParams } = params;
    const env = await makeEnv(services);
    const model = makeFakeModel(modelParams);
    return await mountComponent(CalendarYearRenderer, env, {
        model,
        createRecord() {},
        deleteRecord() {},
        editRecord() {},
        ...props,
    });
}

QUnit.module("CalendarYearRenderer");

QUnit.skipWOWL("mount a CalendarYearRenderer", async (assert) => {
    const calendar = await start({});

    assert.containsN(calendar.el, ".o-calendar-year-renderer--month.fc", 12);
    const monthHeaders = calendar.el.querySelectorAll(".fc-header-toolbar .fc-center");

    // check "title format"
    assert.strictEqual(monthHeaders.length, 12);
    const monthTitles = [
        "Jan 2021",
        "Feb 2021",
        "Mar 2021",
        "Apr 2021",
        "May 2021",
        "Jun 2021",
        "Jul 2021",
        "Aug 2021",
        "Sep 2021",
        "Oct 2021",
        "Nov 2021",
        "Dec 2021",
    ];
    for (let i = 0; i < 12; i++) {
        assert.strictEqual(monthHeaders[i].textContent, monthTitles[i]);
    }
    const dayHeaders = calendar.el
        .querySelector(".o-calendar-year-renderer--month")
        .querySelectorAll(".fc-day-header");

    // check day header format
    assert.strictEqual(dayHeaders.length, 7);
    const dayTitles = ["S", "M", "T", "W", "T", "F", "S"];
    for (let i = 0; i < 7; i++) {
        assert.strictEqual(dayHeaders[i].textContent, dayTitles[i]);
    }

    // check showNonCurrentDates
    assert.containsN(calendar.el, ".fc-day-number", 365);
});

QUnit.skipWOWL("display events", async (assert) => {
    patchWithCleanup(browser, {
        setTimeout: (fn) => fn(),
        clearTimeout: () => {},
    });

    const calendar = await start({
        props: {
            createRecord(record) {
                assert.step(`${record.start.toISODate()} no event`);
            },
        },
        services: {
            popover: makeFakePopoverService((target, _, props) => {
                assert.step(`${props.date.toISODate()} ${props.records[0].title}`);
                return () => {};
            }),
        },
    });

    await clickDate(calendar, "2021-07-15");
    await clickDate(calendar, "2021-07-16");
    await clickDate(calendar, "2021-07-17");

    assert.verifySteps([
        "2021-07-15 no event",
        "2021-07-16 1 day, all day in July",
        "2021-07-17 no event",
    ]);

    await clickDate(calendar, "2021-07-18");
    await clickDate(calendar, "2021-07-19");
    await clickDate(calendar, "2021-07-20");
    await clickDate(calendar, "2021-07-21");

    assert.verifySteps([
        "2021-07-18 3 days, all day in July",
        "2021-07-19 3 days, all day in July",
        "2021-07-20 3 days, all day in July",
        "2021-07-21 no event",
    ]);

    await clickDate(calendar, "2021-06-28");
    await clickDate(calendar, "2021-06-29");
    await clickDate(calendar, "2021-06-30");
    await clickDate(calendar, "2021-07-01");
    await clickDate(calendar, "2021-07-02");
    await clickDate(calendar, "2021-07-03");
    await clickDate(calendar, "2021-07-04");

    assert.verifySteps([
        "2021-06-28 no event",
        "2021-06-29 Over June and July",
        "2021-06-30 Over June and July",
        "2021-07-01 Over June and July",
        "2021-07-02 Over June and July",
        "2021-07-03 Over June and July",
        "2021-07-04 no event",
    ]);
});

QUnit.skipWOWL("click on a date without events", async (assert) => {
    assert.expect(2);

    patchWithCleanup(browser, {
        setTimeout: (fn) => fn(),
        clearTimeout: () => {},
    });

    const calendar = await start({
        props: {
            createRecord(record) {
                assert.ok(record.isAllDay);
                assert.ok(record.start.equals(luxon.DateTime.utc(2021, 6, 1, 0, 0, 0, 0)));
            },
        },
    });

    await clickDate(calendar, "2021-06-01");
});

QUnit.skipWOWL("click on a date with events", async (assert) => {
    assert.expect(1);

    patchWithCleanup(browser, {
        setTimeout: (fn) => fn(),
        clearTimeout: () => {},
    });

    const calendar = await start({});

    await clickDate(calendar, "2021-07-16");

    await nextTick();
    assert.containsOnce(calendar.el, ".o-calendar-year-renderer--popover");
});

QUnit.skipWOWL("select a range of date", async (assert) => {
    assert.expect(3);

    const calendar = await start({
        props: {
            createRecord(record) {
                assert.ok(record.isAllDay);
                assert.ok(record.start.equals(luxon.DateTime.utc(2021, 7, 2, 0, 0, 0, 0)));
                assert.ok(record.end.equals(luxon.DateTime.utc(2021, 7, 6, 0, 0, 0, 0)));
            },
        },
    });

    await selectDateRange(calendar, "2021-07-02", "2021-07-05");
});
