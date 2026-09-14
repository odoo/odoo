import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { markup } from "@odoo/owl";
import { InputConfirmationDialog } from "@portal/js/components/input_confirmation_dialog/input_confirmation_dialog";
import { makeDialogMockEnv, mountWithCleanup } from "@web/../tests/web_test_helpers";

test("a failed confirmation is observable by its caller", async () => {
    await makeDialogMockEnv();
    const component = await mountWithCleanup(InputConfirmationDialog, {
        props: {
            body: markup`<input/>`,
            close: () => expect.step("close"),
            confirm: async () => {
                throw new Error("confirmation failed");
            },
        },
    });
    await expect(component.confirm()).rejects.toThrow("confirmation failed");
    expect.verifySteps(["close"]);
});

test("Enter during IME composition does not confirm", async () => {
    await makeDialogMockEnv();
    await mountWithCleanup(InputConfirmationDialog, {
        props: {
            body: markup`<input/>`,
            close: () => expect.step("close"),
            confirm: () => expect.step("confirm"),
        },
    });
    queryOne("input").dispatchEvent(
        new KeyboardEvent("keydown", {
            key: "Enter",
            isComposing: true,
            bubbles: true,
        }),
    );
    expect.verifySteps([]);
});

test("confirmation validates every control in the input's form before calling its action", async () => {
    await makeDialogMockEnv();
    const component = await mountWithCleanup(InputConfirmationDialog, {
        props: {
            body: markup`<form><input required="required"/><select required="required"><option value="">Choose</option><option value="1">One</option></select></form>`,
            close: () => expect.step("close"),
            confirm: () => expect.step("confirm"),
        },
    });
    await component.confirm();
    expect.verifySteps([]);
    queryOne("input").value = "Description";
    await component.confirm();
    expect.verifySteps([]);
    queryOne("select").value = "1";
    await component.confirm();
    expect.verifySteps(["confirm", "close"]);
});

test("Enter cannot confirm an empty required input", async () => {
    await makeDialogMockEnv();
    await mountWithCleanup(InputConfirmationDialog, {
        props: {
            body: markup`<input required="required"/>`,
            close: () => expect.step("close"),
            confirm: () => expect.step("confirm"),
        },
    });
    queryOne("input").dispatchEvent(
        new KeyboardEvent("keydown", { key: "Enter", bubbles: true }),
    );
    await Promise.resolve();
    expect.verifySteps([]);
});
