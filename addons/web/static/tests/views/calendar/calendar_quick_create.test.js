import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains, getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { FAKE_MODEL } from "./calendar_test_helpers";

import { MainComponentsContainer } from "@web/core/main_components_container";
import { CalendarQuickCreate } from "@web/views/calendar/quick_create/calendar_quick_create";

const FAKE_PROPS = {
    model: FAKE_MODEL,
    record: {},
    editRecord() {},
};

/**
 * @param {{
 *   props?: object;
 *   dialogOptions?: import("@web/core/dialog/dialog_service").DialogServiceInterfaceAddOptions;
 * }} [params]
 */
async function start(params = {}) {
    await mountWithCleanup(MainComponentsContainer);
    getService("dialog").add(
        CalendarQuickCreate,
        { ...FAKE_PROPS, ...params.props },
        params.dialogOptions
    );
    await waitFor(`.o_dialog`);
}

test.tags("desktop")(`mount a CalendarQuickCreate`, async () => {
    await start();
    expect(`.o-calendar-quick-create`).toHaveCount(1);
    expect(`.o_dialog .modal-sm`).toHaveCount(1);
    expect(`.modal-title`).toHaveText("New Event");
    expect(`input[name="title"]`).toBeFocused();
    expect(`.o-calendar-quick-create--create-btn`).toHaveCount(1);
    expect(`.o-calendar-quick-create--edit-btn`).toHaveCount(1);
    expect(`.o-calendar-quick-create--cancel-btn`).toHaveCount(1);
});

test(`click on create button`, async () => {
    await start({
        props: {
            model: { ...FAKE_MODEL, createRecord: () => expect.step("create") },
        },
        dialogOptions: { onClose: () => expect.step("close") },
    });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect.verifySteps([]);
    expect(`input[name=title]`).toHaveClass("o_field_invalid");
});

test(`click on create button (with name)`, async () => {
    await start({
        props: {
            model: {
                ...FAKE_MODEL,
                createRecord(record) {
                    expect.step("create");
                    expect(record.title).toBe("TEST");
                },
            },
        },
        dialogOptions: { onClose: () => expect.step("close") },
    });
    await contains(`.o-calendar-quick-create--input`).edit("TEST", { confirm: "blur" });
    await contains(`.o-calendar-quick-create--create-btn`).click();
    expect.verifySteps(["create", "close"]);
});

test(`click on edit button`, async () => {
    await start({
        props: { editRecord: () => expect.step("edit") },
        dialogOptions: { onClose: () => expect.step("close") },
    });
    await contains(`.o-calendar-quick-create--edit-btn`).click();
    expect.verifySteps(["edit", "close"]);
});

test(`click on edit button (with name)`, async () => {
    await start({
        props: {
            editRecord(record) {
                expect.step("edit");
                expect(record.title).toBe("TEST");
            },
        },
        dialogOptions: { onClose: () => expect.step("close") },
    });
    await contains(`.o-calendar-quick-create--input`).edit("TEST", { confirm: "blur" });
    await contains(`.o-calendar-quick-create--edit-btn`).click();
    expect.verifySteps(["edit", "close"]);
});

test(`click on cancel button`, async () => {
    await start({
        dialogOptions: { onClose: () => expect.step("close") },
    });
    await contains(`.o-calendar-quick-create--cancel-btn`).click();
    expect.verifySteps(["close"]);
});

test(`check default title`, async () => {
    await start({
        props: { title: "Example Title" },
    });
    expect(`.o-calendar-quick-create--input`).toHaveValue("Example Title");
});
