/** @odoo-module **/

import { CalendarYearPopover } from "@web/views/calendar/calendar_year/calendar_year_popover";
import { click } from "../../helpers/utils";
import {
    FAKE_DATE,
    mountComponent,
    makeEnv,
    makeFakeModel,
    FAKE_RECORDS,
} from "./calendar_helpers";

const FAKE_POPOVER_RECORDS = [
    {
        id: 1,
        start: FAKE_DATE,
        end: FAKE_DATE,
        isAllDay: true,
        title: "R1",
    },
    {
        id: 2,
        start: FAKE_DATE.set({ hours: 14 }),
        end: FAKE_DATE.set({ hours: 16 }),
        isAllDay: false,
        title: "R2",
    },
    {
        id: 3,
        start: FAKE_DATE.minus({ days: 1 }),
        end: FAKE_DATE.plus({ days: 1 }),
        isAllDay: true,
        title: "R3",
    },
    {
        id: 4,
        start: FAKE_DATE.minus({ days: 3 }),
        end: FAKE_DATE.plus({ days: 1 }),
        isAllDay: true,
        title: "R4",
    },
    {
        id: 5,
        start: FAKE_DATE.minus({ days: 1 }),
        end: FAKE_DATE.plus({ days: 3 }),
        isAllDay: true,
        title: "R5",
    },
];

async function start(params = {}) {
    const { services, props, model: modelParams } = params;
    const env = await makeEnv(services);
    const model = makeFakeModel(modelParams);
    return await mountComponent(CalendarYearPopover, env, {
        model,
        date: FAKE_DATE,
        records: FAKE_POPOVER_RECORDS,
        createRecord() {},
        deleteRecord() {},
        editRecord() {},
        ...props,
    });
}

QUnit.module("CalendarYearPopover");

QUnit.skipWOWL("canCreate is true", async (assert) => {
    const popover = await start({ model: { canCreate: true } });
    assert.containsOnce(
        popover.el,
        ".o-calendar-year-popover--footer .o-calendar-year-popover--create-button"
    );
});

QUnit.skipWOWL("canCreate is false", async (assert) => {
    const popover = await start({ model: { canCreate: false } });
    assert.containsNone(
        popover.el,
        ".o-calendar-year-popover--footer .o-calendar-year-popover--create-button"
    );
});

QUnit.skipWOWL("click on create button", async (assert) => {
    assert.expect(3);
    const popover = await start({
        props: {
            createRecord: () => assert.step("create"),
        },
        model: { canCreate: true },
    });
    assert.containsOnce(
        popover.el,
        ".o-calendar-year-popover--footer .o-calendar-year-popover--create-button"
    );
    await click(popover.el, ".o-calendar-year-popover--create-button");
    assert.verifySteps(["create"]);
});

QUnit.skipWOWL("group records", async (assert) => {
    const popover = await start({});

    assert.containsN(popover.el, ".o-calendar-year-popover--section", 4);
    assert.containsN(popover.el, ".o-calendar-year-popover--record", 5);

    const sectionTitles = popover.el.querySelectorAll(".o-calendar-year-popover--section-title");
    assert.strictEqual(sectionTitles[0].textContent.trim(), "July 16, 2021");
    assert.strictEqual(sectionTitles[1].textContent.trim(), "July 13-17, 2021");
    assert.strictEqual(sectionTitles[2].textContent.trim(), "July 15-17, 2021");
    assert.strictEqual(sectionTitles[3].textContent.trim(), "July 15-19, 2021");

    const sections = popover.el.querySelectorAll(".o-calendar-year-popover--section");
    assert.strictEqual(sections[0].textContent.trim(), "July 16, 2021R1 R2 14:00");
    assert.strictEqual(sections[1].textContent.trim(), "July 13-17, 2021R4");
    assert.strictEqual(sections[2].textContent.trim(), "July 15-17, 2021R3");
    assert.strictEqual(sections[3].textContent.trim(), "July 15-19, 2021R5");
});

QUnit.skipWOWL("click on record", async (assert) => {
    assert.expect(3);
    const popover = await start({
        props: {
            records: [FAKE_RECORDS[3]],
            editRecord: () => assert.step("edit"),
        },
    });
    assert.containsOnce(popover.el, ".o-calendar-year-popover--record");
    await click(popover.el, ".o-calendar-year-popover--record");
    assert.verifySteps(["edit"]);
});
