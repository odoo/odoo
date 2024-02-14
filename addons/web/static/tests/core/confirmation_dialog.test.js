import { expect, test, describe, destroy } from "@odoo/hoot";
import { tick, Deferred } from "@odoo/hoot-mock";
import { press } from "@odoo/hoot-dom";
import { mountWithCleanup, contains, makeDialogMockEnv } from "@web/../tests/web_test_helpers";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component, xml } from "@odoo/owl";

describe.current.tags("desktop");

test("check content confirmation dialog", async () => {
    const env = await makeDialogMockEnv();
    await mountWithCleanup(ConfirmationDialog, {
        env,
        props: {
            body: "Some content",
            title: "Confirmation",
            close: () => {},
            confirm: () => {},
            cancel: () => {},
        },
    });
    expect(".modal-header").toHaveText("Confirmation");
    expect(".modal-body").toHaveText("Some content");
});

test("pressing escape to close the dialog", async () => {
    const env = await makeDialogMockEnv();
    await mountWithCleanup(ConfirmationDialog, {
        env,
        props: {
            body: "Some content",
            title: "Confirmation",
            close: () => {
                expect.step("Close action");
            },
            confirm: () => {},
            cancel: () => {
                expect.step("Cancel action");
            },
        },
    });
    expect([]).toVerifySteps();
    press("escape");
    await tick();
    expect(["Cancel action", "Close action"]).toVerifySteps();
});

test("clicking on 'Ok'", async () => {
    const env = await makeDialogMockEnv();
    await mountWithCleanup(ConfirmationDialog, {
        env,
        props: {
            body: "Some content",
            title: "Confirmation",
            close: () => {
                expect.step("Close action");
            },
            confirm: () => {
                expect.step("Confirm action");
            },
            cancel: () => {
                throw new Error("should not be called");
            },
        },
    });
    expect([]).toVerifySteps();
    await contains(".modal-footer .btn-primary").click();
    expect(["Confirm action", "Close action"]).toVerifySteps();
});

test("clicking on 'Cancel'", async () => {
    const env = await makeDialogMockEnv();
    await mountWithCleanup(ConfirmationDialog, {
        env,
        props: {
            body: "Some content",
            title: "Confirmation",
            close: () => {
                expect.step("Close action");
            },
            confirm: () => {
                throw new Error("should not be called");
            },
            cancel: () => {
                expect.step("Cancel action");
            },
        },
    });
    expect([]).toVerifySteps();
    await contains(".modal-footer .btn-secondary").click();
    expect(["Cancel action", "Close action"]).toVerifySteps();
});

test("can't click twice on 'Ok'", async () => {
    const env = await makeDialogMockEnv();
    await mountWithCleanup(ConfirmationDialog, {
        env,
        props: {
            body: "Some content",
            title: "Confirmation",
            close: () => {},
            confirm: () => {
                expect.step("Confirm action");
            },
            cancel: () => {},
        },
    });
    expect([]).toVerifySteps();
    expect(".modal-footer .btn-primary").not.toHaveAttribute("disabled");
    expect(".modal-footer .btn-secondary").not.toHaveAttribute("disabled");
    await contains(".modal-footer .btn-primary").click();
    expect(".modal-footer .btn-primary").toHaveAttribute("disabled");
    expect(".modal-footer .btn-secondary").toHaveAttribute("disabled");
    expect(["Confirm action"]).toVerifySteps();
});

test("can't click twice on 'Cancel'", async () => {
    const env = await makeDialogMockEnv();
    await mountWithCleanup(ConfirmationDialog, {
        env,
        props: {
            body: "Some content",
            title: "Confirmation",
            close: () => {},
            confirm: () => {},
            cancel: () => {
                expect.step("Cancel action");
            },
        },
    });
    expect([]).toVerifySteps();
    expect(".modal-footer .btn-primary").not.toHaveAttribute("disabled");
    expect(".modal-footer .btn-secondary").not.toHaveAttribute("disabled");
    await contains(".modal-footer .btn-secondary").click();
    expect(".modal-footer .btn-primary").toHaveAttribute("disabled");
    expect(".modal-footer .btn-secondary").toHaveAttribute("disabled");
    expect(["Cancel action"]).toVerifySteps();
});

test("can't cancel (with escape) after confirm", async () => {
    const def = new Deferred();
    const env = await makeDialogMockEnv();
    await mountWithCleanup(ConfirmationDialog, {
        env,
        props: {
            body: "Some content",
            title: "Confirmation",
            close: () => {
                expect.step("Close action");
            },
            confirm: () => {
                expect.step("Confirm action");
                return def;
            },
            cancel: () => {
                throw new Error("should not cancel");
            },
        },
    });
    await contains(".modal-footer .btn-primary").click();
    expect(["Confirm action"]).toVerifySteps();
    press("escape");
    await tick();
    expect([]).toVerifySteps();
    def.resolve();
    await tick();
    expect(["Close action"]).toVerifySteps();
});

test("wait for confirm callback before closing", async () => {
    const def = new Deferred();
    const env = await makeDialogMockEnv();
    await mountWithCleanup(ConfirmationDialog, {
        env,
        props: {
            body: "Some content",
            title: "Confirmation",
            close: () => {
                expect.step("Close action");
            },
            confirm: () => {
                expect.step("Confirm action");
                return def;
            },
        },
    });
    await contains(".modal-footer .btn-primary").click();
    expect(["Confirm action"]).toVerifySteps();
    def.resolve();
    await tick();
    expect(["Close action"]).toVerifySteps();
});

test("Focus is correctly restored after confirmation", async () => {
    const env = await makeDialogMockEnv();

    class Parent extends Component {
        static template = xml`<div class="my-comp"><input type="text" class="my-input"/></div>`;
        static props = ["*"];
    }

    await mountWithCleanup(Parent, { env });
    await contains(".my-input").focus();
    expect(".my-input").toBeFocused();

    const dialog = await mountWithCleanup(ConfirmationDialog, {
        env,
        props: {
            body: "Some content",
            title: "Confirmation",
            confirm: () => {},
            close: () => {},
        },
    });
    expect(".modal-footer .btn-primary").toBeFocused();
    await contains(".modal-footer .btn-primary").click();
    expect(document.body).toBeFocused();
    destroy(dialog);
    expect(".my-input").toBeFocused();
});
