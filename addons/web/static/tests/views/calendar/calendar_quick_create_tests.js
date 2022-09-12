/** @odoo-module **/

import { CalendarQuickCreate } from "@web/views/calendar/quick_create/calendar_quick_create";
import { click } from "../../helpers/utils";
import { makeEnv, makeFakeModel, mountComponent } from "./calendar_helpers";

async function start(params = {}) {
    const { services, props, model: modelParams } = params;
    const env = await makeEnv(services);
    const model = makeFakeModel(modelParams);
    return await mountComponent(CalendarQuickCreate, env, {
        model,
        record: {},
        close() {},
        editRecord() {},
        ...props,
    });
}

QUnit.module("CalendarQuickCreate");

QUnit.skipWOWL("mount a CalendarQuickCreate", async (assert) => {
    const quickCreate = await start({});
    assert.containsOnce(quickCreate.el, ".o-calendar-quick-create");
    assert.containsOnce(quickCreate.el, ".o_dialog .modal-sm");
    assert.strictEqual(quickCreate.el.querySelector(".modal-title").textContent, "New Event");
    assert.strictEqual(quickCreate.el.querySelector(`input[name="name"]`), document.activeElement);
    assert.containsOnce(quickCreate.el, ".o-calendar-quick-create--create-btn");
    assert.containsOnce(quickCreate.el, ".o-calendar-quick-create--edit-btn");
    assert.containsOnce(quickCreate.el, ".o-calendar-quick-create--cancel-btn");
});

QUnit.skipWOWL("click on create button", async (assert) => {
    assert.expect(3);
    const quickCreate = await start({
        props: {
            close: () => assert.step("close"),
        },
        model: {
            createRecord: () => assert.step("create"),
        },
    });
    await click(quickCreate.el, ".o-calendar-quick-create--create-btn");
    assert.verifySteps(["create", "close"]);
});

QUnit.skipWOWL("click on create button (with name)", async (assert) => {
    assert.expect(4);
    const quickCreate = await start({
        props: {
            close: () => assert.step("close"),
        },
        model: {
            createRecord(record) {
                assert.step("create");
                assert.strictEqual(record.title, "TEST");
            },
        },
    });

    const input = quickCreate.el.querySelector(".o-calendar-quick-create--input");
    input.value = "TEST";

    await click(quickCreate.el, ".o-calendar-quick-create--create-btn");
    assert.verifySteps(["create", "close"]);
});

QUnit.skipWOWL("click on edit button", async (assert) => {
    assert.expect(3);
    const quickCreate = await start({
        props: {
            close: () => assert.step("close"),
            editRecord: () => assert.step("edit"),
        },
    });
    await click(quickCreate.el, ".o-calendar-quick-create--edit-btn");
    assert.verifySteps(["edit", "close"]);
});

QUnit.skipWOWL("click on edit button (with name)", async (assert) => {
    assert.expect(4);
    const quickCreate = await start({
        props: {
            close: () => assert.step("close"),
            editRecord(record) {
                assert.step("edit");
                assert.strictEqual(record.title, "TEST");
            },
        },
    });

    const input = quickCreate.el.querySelector(".o-calendar-quick-create--input");
    input.value = "TEST";

    await click(quickCreate.el, ".o-calendar-quick-create--edit-btn");
    assert.verifySteps(["edit", "close"]);
});

QUnit.skipWOWL("click on cancel button", async (assert) => {
    assert.expect(2);
    const quickCreate = await start({
        props: {
            close: () => assert.step("close"),
        },
    });
    await click(quickCreate.el, ".o-calendar-quick-create--cancel-btn");
    assert.verifySteps(["close"]);
});
