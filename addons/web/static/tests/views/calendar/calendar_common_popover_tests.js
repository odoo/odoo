/** @odoo-module **/

import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { click, getFixture } from "../../helpers/utils";
import { makeEnv, makeFakeDate, makeFakeModel, mountComponent } from "./helpers";

let target;

function makeFakeRecord(data = {}) {
    return {
        id: 5,
        title: "Meeting",
        isAllDay: false,
        start: makeFakeDate(),
        end: makeFakeDate().plus({ hours: 3, minutes: 15 }),
        colorIndex: 0,
        isTimeHidden: false,
        rawRecord: {
            name: "Meeting",
        },
        ...data,
    };
}

async function start(params = {}) {
    const { services, props, model: modelParams } = params;
    const env = await makeEnv(services);
    const model = makeFakeModel(modelParams);
    return await mountComponent(CalendarCommonPopover, env, {
        model,
        record: makeFakeRecord(),
        createRecord() {},
        deleteRecord() {},
        editRecord() {},
        close() {},
        ...props,
    });
}

/** @todo Add tests for fields **/

QUnit.module("CalendarView - CommonPopover", ({ beforeEach }) => {
    beforeEach(() => {
        target = getFixture();
    });

    QUnit.test("mount a CalendarCommonPopover", async (assert) => {
        await start({});
        assert.containsOnce(target, ".popover-header");
        assert.strictEqual(target.querySelector(".popover-header").textContent, "Meeting");
        assert.containsN(target, ".list-group", 2);
        assert.containsOnce(target, ".list-group.o_cw_popover_fields_secondary");
        assert.containsOnce(target, ".card-footer .o_cw_popover_edit");
        assert.containsOnce(target, ".card-footer .o_cw_popover_delete");
    });

    QUnit.test("date duration: is all day and is same day", async (assert) => {
        await start({
            props: {
                record: makeFakeRecord({ isAllDay: true, isTimeHidden: true }),
            },
        });
        const dateTimeGroup = target.querySelector(`.list-group`);
        const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
        assert.strictEqual(dateTimeLabels, "July 16, 2021 (All day)");
    });

    QUnit.test("date duration: is all day and two days duration", async (assert) => {
        await start({
            props: {
                record: makeFakeRecord({
                    end: makeFakeDate().plus({ days: 1 }),
                    isAllDay: true,
                    isTimeHidden: true,
                }),
            },
        });
        const dateTimeGroup = target.querySelector(`.list-group`);
        const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
        assert.strictEqual(dateTimeLabels, "July 16-17, 2021 (2 days)");
    });

    QUnit.test("time duration: 1 hour diff", async (assert) => {
        await start({
            props: {
                record: makeFakeRecord({ end: makeFakeDate().plus({ hours: 1 }) }),
            },
            model: { isDateHidden: true },
        });
        const dateTimeGroup = target.querySelector(`.list-group`);
        const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
        assert.strictEqual(dateTimeLabels, "08:00 - 09:00 (1 hour)");
    });

    QUnit.test("time duration: 2 hours diff", async (assert) => {
        await start({
            props: {
                record: makeFakeRecord({ end: makeFakeDate().plus({ hours: 2 }) }),
            },
            model: { isDateHidden: true },
        });
        const dateTimeGroup = target.querySelector(`.list-group`);
        const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
        assert.strictEqual(dateTimeLabels, "08:00 - 10:00 (2 hours)");
    });

    QUnit.test("time duration: 1 minute diff", async (assert) => {
        await start({
            props: {
                record: makeFakeRecord({ end: makeFakeDate().plus({ minutes: 1 }) }),
            },
            model: { isDateHidden: true },
        });
        const dateTimeGroup = target.querySelector(`.list-group`);
        const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
        assert.strictEqual(dateTimeLabels, "08:00 - 08:01 (1 minute)");
    });

    QUnit.test("time duration: 2 minutes diff", async (assert) => {
        await start({
            props: {
                record: makeFakeRecord({ end: makeFakeDate().plus({ minutes: 2 }) }),
            },
            model: { isDateHidden: true },
        });
        const dateTimeGroup = target.querySelector(`.list-group`);
        const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
        assert.strictEqual(dateTimeLabels, "08:00 - 08:02 (2 minutes)");
    });

    QUnit.test("time duration: 3 hours and 15 minutes diff", async (assert) => {
        await start({
            model: { isDateHidden: true },
        });
        const dateTimeGroup = target.querySelector(`.list-group`);
        const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
        assert.strictEqual(dateTimeLabels, "08:00 - 11:15 (3 hours, 15 minutes)");
    });

    QUnit.test("isDateHidden is true", async (assert) => {
        await start({
            model: { isDateHidden: true },
        });
        const dateTimeGroup = target.querySelector(`.list-group`);
        const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
        assert.strictEqual(dateTimeLabels, "08:00 - 11:15 (3 hours, 15 minutes)");
    });

    QUnit.test("isDateHidden is false", async (assert) => {
        await start({
            model: { isDateHidden: false },
        });
        const dateTimeGroup = target.querySelector(`.list-group`);
        const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
        assert.strictEqual(
            dateTimeLabels,
            "July 16, 2021 08:00 - 11:15 (3 hours, 15 minutes)"
        );
    });

    QUnit.test("isTimeHidden is true", async (assert) => {
        await start({
            props: {
                record: makeFakeRecord({ isTimeHidden: true }),
            },
        });
        const dateTimeGroup = target.querySelector(`.list-group`);
        const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
        assert.strictEqual(dateTimeLabels, "July 16, 2021");
    });

    QUnit.test("isTimeHidden is false", async (assert) => {
        await start({
            props: {
                record: makeFakeRecord({ isTimeHidden: false }),
            },
        });
        const dateTimeGroup = target.querySelector(`.list-group`);
        const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
        assert.strictEqual(
            dateTimeLabels,
            "July 16, 2021 08:00 - 11:15 (3 hours, 15 minutes)"
        );
    });

    QUnit.test("canDelete is true", async (assert) => {
        await start({
            model: { canDelete: true },
        });
        assert.containsOnce(target, ".o_cw_popover_delete");
    });

    QUnit.test("canDelete is false", async (assert) => {
        await start({
            model: { canDelete: false },
        });
        assert.containsNone(target, ".o_cw_popover_delete");
    });

    QUnit.test("click on delete button", async (assert) => {
        assert.expect(2);
        await start({
            model: { canDelete: true },
            props: {
                deleteRecord: () => assert.step("delete"),
            },
        });
        await click(target, ".o_cw_popover_delete");
        assert.verifySteps(["delete"]);
    });

    QUnit.test("click on edit button", async (assert) => {
        assert.expect(2);
        await start({
            props: {
                editRecord: () => assert.step("edit"),
            },
        });
        await click(target, ".o_cw_popover_edit");
        assert.verifySteps(["edit"]);
    });
});
