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

test("Without dismiss callback: pressing escape to close the dialog", async () => {
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
    expect.verifySteps([]);
    await press("escape");
    await tick();
    expect.verifySteps(["Cancel action", "Close action"]);
});

test("With dismiss callback: pressing escape to close the dialog", async () => {
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
                throw new Error("should not be called");
            },
            dismiss: () => {
                expect.step("Dismiss action");
            },
        },
    });
    await press("escape");
    await tick();
    expect.verifySteps(["Dismiss action", "Close action"]);
});

test("Without dismiss callback: clicking on 'X' to close the dialog", async () => {
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
    await contains(".modal-header .btn-close").click();
    expect.verifySteps(["Cancel action", "Close action"]);
});

test("With dismiss callback: clicking on 'X' to close the dialog", async () => {
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
                throw new Error("should not be called");
            },
            dismiss: () => {
                expect.step("Dismiss action");
            },
        },
    });
    await contains(".modal-header .btn-close").click();
    expect.verifySteps(["Dismiss action", "Close action"]);
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
    expect.verifySteps([]);
    await contains(".modal-footer .btn-primary").click();
    expect.verifySteps(["Confirm action", "Close action"]);
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
    expect.verifySteps([]);
    await contains(".modal-footer .btn-secondary").click();
    expect.verifySteps(["Cancel action", "Close action"]);
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
    expect.verifySteps([]);
    expect(".modal-footer .btn-primary").not.toHaveAttribute("disabled");
    expect(".modal-footer .btn-secondary").not.toHaveAttribute("disabled");
    await contains(".modal-footer .btn-primary").click();
    expect(".modal-footer .btn-primary").toHaveAttribute("disabled");
    expect(".modal-footer .btn-secondary").toHaveAttribute("disabled");
    expect.verifySteps(["Confirm action"]);
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
    expect.verifySteps([]);
    expect(".modal-footer .btn-primary").not.toHaveAttribute("disabled");
    expect(".modal-footer .btn-secondary").not.toHaveAttribute("disabled");
    await contains(".modal-footer .btn-secondary").click();
    expect(".modal-footer .btn-primary").toHaveAttribute("disabled");
    expect(".modal-footer .btn-secondary").toHaveAttribute("disabled");
    expect.verifySteps(["Cancel action"]);
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
    expect.verifySteps(["Confirm action"]);
    await press("escape");
    await tick();
    expect.verifySteps([]);
    def.resolve();
    await tick();
    expect.verifySteps(["Close action"]);
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
    expect.verifySteps(["Confirm action"]);
    def.resolve();
    await tick();
    expect.verifySteps(["Close action"]);
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
    await Promise.resolve();
    expect(".my-input").toBeFocused();
});
