/** @odoo-module **/

import { CalendarYearPopover } from "@web/views/calendar/calendar_year/calendar_year_popover";
import { click, getFixture } from "../../helpers/utils";
import { mountComponent, makeEnv, makeFakeModel, makeFakeRecords, makeFakeDate } from "./helpers";

let target, fakePopoverRecords;

async function start(params = {}) {
    const { services, props, model: modelParams } = params;
    const env = await makeEnv(services);
    const model = makeFakeModel(modelParams);
    return await mountComponent(CalendarYearPopover, env, {
        model,
        date: makeFakeDate(),
        records: fakePopoverRecords,
        createRecord() {},
        deleteRecord() {},
        editRecord() {},
        close() {},
        ...props,
    });
}

QUnit.module("CalendarView - YearPopover", ({ beforeEach }) => {
    beforeEach(() => {
        target = getFixture();
        fakePopoverRecords = [
            {
                id: 1,
                start: makeFakeDate(),
                end: makeFakeDate(),
                isAllDay: true,
                title: "R1",
            },
            {
                id: 2,
                start: makeFakeDate().set({ hours: 14 }),
                end: makeFakeDate().set({ hours: 16 }),
                isAllDay: false,
                title: "R2",
            },
            {
                id: 3,
                start: makeFakeDate().minus({ days: 1 }),
                end: makeFakeDate().plus({ days: 1 }),
                isAllDay: true,
                title: "R3",
            },
            {
                id: 4,
                start: makeFakeDate().minus({ days: 3 }),
                end: makeFakeDate().plus({ days: 1 }),
                isAllDay: true,
                title: "R4",
            },
            {
                id: 5,
                start: makeFakeDate().minus({ days: 1 }),
                end: makeFakeDate().plus({ days: 3 }),
                isAllDay: true,
                title: "R5",
            },
        ];
    });

    QUnit.test("canCreate is true", async (assert) => {
        await start({ model: { canCreate: true } });
        assert.containsOnce(target, ".o_cw_popover_create");
    });

    QUnit.test("canCreate is false", async (assert) => {
        await start({ model: { canCreate: false } });
        assert.containsNone(target, ".o_cw_popover_create");
    });

    QUnit.test("click on create button", async (assert) => {
        assert.expect(3);
        await start({
            props: {
                createRecord: () => assert.step("create"),
            },
            model: { canCreate: true },
        });
        assert.containsOnce(target, ".o_cw_popover_create");
        await click(target, ".o_cw_popover_create");
        assert.verifySteps(["create"]);
    });

    QUnit.test("group records", async (assert) => {
        await start({});

        assert.containsN(target, ".o_cw_body > div", 4);
        assert.containsN(target, ".o_cw_body > a", 1);

        const sectionTitles = target.querySelectorAll(".o_cw_body > div");
        assert.strictEqual(sectionTitles[0].textContent.trim(), "July 16, 2021R114:00R2");
        assert.strictEqual(sectionTitles[1].textContent.trim(), "July 13-17, 2021R4");
        assert.strictEqual(sectionTitles[2].textContent.trim(), "July 15-17, 2021R3");
        assert.strictEqual(sectionTitles[3].textContent.trim(), "July 15-19, 2021R5");

        assert.strictEqual(
            target.querySelector(".o_cw_body").textContent.trim(),
            "July 16, 2021R114:00R2July 13-17, 2021R4July 15-17, 2021R3July 15-19, 2021R5 Create"
        );
    });

    QUnit.test("click on record", async (assert) => {
        assert.expect(3);
        await start({
            props: {
                records: [makeFakeRecords()[3]],
                editRecord: () => assert.step("edit"),
            },
        });
        assert.containsOnce(target, ".o_cw_body a.o_cw_popover_link");
        await click(target, ".o_cw_body a.o_cw_popover_link");
        assert.verifySteps(["edit"]);
    });
});
