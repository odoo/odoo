/** @odoo-module **/

import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { click } from "../../helpers/utils";
import { FAKE_DATE, makeEnv, makeFakeModel, mountComponent } from "./calendar_helpers";

function makeFakeRecord(data = {}) {
    return {
        id: 5,
        title: "Meeting",
        isAllDay: false,
        start: FAKE_DATE,
        end: FAKE_DATE.plus({ hours: 3, minutes: 15 }),
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
        ...props,
    });
}

/** @todo Add tests for fields **/

QUnit.module("CalendarCommonPopover");

QUnit.skipWOWL("mount a CalendarCommonPopover", async (assert) => {
    const popover = await start({});
    assert.containsOnce(popover.el, ".popover-header");
    assert.strictEqual(popover.el.querySelector(".popover-header").textContent, "Meeting");
    assert.containsN(popover.el, ".list-group", 2);
    assert.containsOnce(popover.el, ".list-group.o_cw_popover_fields_secondary");
    assert.containsOnce(popover.el, ".card-footer .o_cw_popover_edit");
    assert.containsOnce(popover.el, ".card-footer .o_cw_popover_delete");
});

QUnit.skipWOWL("date duration: is all day and is same day", async (assert) => {
    const popover = await start({
        props: {
            record: makeFakeRecord({ isAllDay: true, isTimeHidden: true }),
        },
    });
    const dateTimeGroup = popover.el.querySelector(`.list-group`);
    const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
    assert.strictEqual(dateTimeLabels, "Friday, July 16, 2021 (All day)");
});

QUnit.skipWOWL("date duration: is all day but 1 day diff", async (assert) => {
    const popover = await start({
        props: {
            record: makeFakeRecord({
                end: FAKE_DATE.plus({ days: 1 }),
                isAllDay: true,
                isTimeHidden: true,
            }),
        },
    });
    const dateTimeGroup = popover.el.querySelector(`.list-group`);
    const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
    assert.strictEqual(dateTimeLabels, "July 16-17, 2021 (1 day)");
    popover.destroy();
});

QUnit.skipWOWL("date duration: is all day but 2 days diff", async (assert) => {
    const popover = await start({
        props: {
            record: makeFakeRecord({
                end: FAKE_DATE.plus({ days: 2 }),
                isAllDay: true,
                isTimeHidden: true,
            }),
        },
    });
    const dateTimeGroup = popover.el.querySelector(`.list-group`);
    const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
    assert.strictEqual(dateTimeLabels, "July 16-18, 2021 (2 days)");
    popover.destroy();
});

QUnit.skipWOWL("time duration: 1 hour diff", async (assert) => {
    const popover = await start({
        props: {
            record: makeFakeRecord({ end: FAKE_DATE.plus({ hours: 1 }) }),
        },
        model: { isDateHidden: true },
    });
    const dateTimeGroup = popover.el.querySelector(`.list-group`);
    const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
    assert.strictEqual(dateTimeLabels, "10:00 - 11:00 (1 hour)");
    popover.destroy();
});

QUnit.skipWOWL("time duration: 2 hours diff", async (assert) => {
    const popover = await start({
        props: {
            record: makeFakeRecord({ end: FAKE_DATE.plus({ hours: 2 }) }),
        },
        model: { isDateHidden: true },
    });
    const dateTimeGroup = popover.el.querySelector(`.list-group`);
    const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
    assert.strictEqual(dateTimeLabels, "10:00 - 12:00 (2 hours)");
    popover.destroy();
});

QUnit.skipWOWL("time duration: 1 minute diff", async (assert) => {
    const popover = await start({
        props: {
            record: makeFakeRecord({ end: FAKE_DATE.plus({ minutes: 1 }) }),
        },
        model: { isDateHidden: true },
    });
    const dateTimeGroup = popover.el.querySelector(`.list-group`);
    const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
    assert.strictEqual(dateTimeLabels, "10:00 - 10:01 (1 minute)");
    popover.destroy();
});

QUnit.skipWOWL("time duration: 2 minutes diff", async (assert) => {
    const popover = await start({
        props: {
            record: makeFakeRecord({ end: FAKE_DATE.plus({ minutes: 2 }) }),
        },
        model: { isDateHidden: true },
    });
    const dateTimeGroup = popover.el.querySelector(`.list-group`);
    const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
    assert.strictEqual(dateTimeLabels, "10:00 - 10:02 (2 minutes)");
    popover.destroy();
});

QUnit.skipWOWL("time duration: 3 hours and 15 minutes diff", async (assert) => {
    const popover = await start({
        model: { isDateHidden: true },
    });
    const dateTimeGroup = popover.el.querySelector(`.list-group`);
    const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
    assert.strictEqual(dateTimeLabels, "10:00 - 13:15 (3 hours, 15 minutes)");
    popover.destroy();
});

QUnit.skipWOWL("isDateHidden is true", async (assert) => {
    const popover = await start({
        model: { isDateHidden: true },
    });
    const dateTimeGroup = popover.el.querySelector(`.list-group`);
    const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
    assert.strictEqual(dateTimeLabels, "10:00 - 13:15 (3 hours, 15 minutes)");
    popover.destroy();
});

QUnit.skipWOWL("isDateHidden is false", async (assert) => {
    const popover = await start({
        model: { isDateHidden: false },
    });
    const dateTimeGroup = popover.el.querySelector(`.list-group`);
    const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
    assert.strictEqual(dateTimeLabels, "Friday, July 16, 2021 10:00 - 13:15 (3 hours, 15 minutes)");
    popover.destroy();
});

QUnit.skipWOWL("isTimeHidden is true", async (assert) => {
    const popover = await start({
        props: {
            record: makeFakeRecord({ isTimeHidden: true }),
        },
    });
    const dateTimeGroup = popover.el.querySelector(`.list-group`);
    const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
    assert.strictEqual(dateTimeLabels, "Friday, July 16, 2021");
    popover.destroy();
});

QUnit.skipWOWL("isTimeHidden is false", async (assert) => {
    const popover = await start({
        props: {
            record: makeFakeRecord({ isTimeHidden: false }),
        },
    });
    const dateTimeGroup = popover.el.querySelector(`.list-group`);
    const dateTimeLabels = dateTimeGroup.textContent.replace(/\s+/g, " ").trim();
    assert.strictEqual(dateTimeLabels, "Friday, July 16, 2021 10:00 - 13:15 (3 hours, 15 minutes)");
    popover.destroy();
});

QUnit.skipWOWL("canDelete is true", async (assert) => {
    const popover = await start({
        model: { canDelete: true },
    });
    assert.containsOnce(popover.el, ".o_cw_popover_delete");
    popover.destroy();
});

QUnit.skipWOWL("canDelete is false", async (assert) => {
    const popover = await start({
        model: { canDelete: false },
    });
    assert.containsNone(popover.el, ".o_cw_popover_delete");
    popover.destroy();
});

QUnit.skipWOWL("click on delete button", async (assert) => {
    assert.expect(2);
    const popover = await start({
        model: { canDelete: true },
        props: {
            deleteRecord: () => assert.step("delete"),
        },
    });
    await click(popover.el, ".o_cw_popover_delete");
    assert.verifySteps(["delete"]);
    popover.destroy();
});

QUnit.skipWOWL("click on edit button", async (assert) => {
    assert.expect(2);
    const popover = await start({
        props: {
            editRecord: () => assert.step("edit"),
        },
    });
    await click(popover.el, ".o_cw_popover_edit");
    assert.verifySteps(["edit"]);
    popover.destroy();
});
