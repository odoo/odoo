/** @odoo-module **/

import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeDialogTestEnv } from "../helpers/mock_env";
import {
    click,
    destroy,
    getFixture,
    makeDeferred,
    mount,
    nextTick,
    triggerHotkey,
} from "../helpers/utils";
import { makeFakeDialogService } from "../helpers/mock_services";
import { Component, xml } from "@odoo/owl";

const serviceRegistry = registry.category("services");
let target;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async (assert) => {
        target = getFixture();
        async function addDialog(dialogClass, props) {
            assert.strictEqual(props.body, "Some content");
            assert.strictEqual(props.title, "Confirmation");
        }
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("dialog", makeFakeDialogService(addDialog), { force: true });
    });

    QUnit.module("ConfirmationDialog");

    QUnit.test("pressing escape to close the dialog", async function (assert) {
        const env = await makeDialogTestEnv();
        await mount(ConfirmationDialog, target, {
            env,
            props: {
                body: "Some content",
                title: "Confirmation",
                close: () => {
                    assert.step("Close action");
                },
                confirm: () => {},
                cancel: () => {
                    assert.step("Cancel action");
                },
            },
        });
        assert.verifySteps([]);
        triggerHotkey("escape");
        await nextTick();
        assert.verifySteps(
            ["Cancel action", "Close action"],
            "dialog has called its cancel method before its closure"
        );
    });

    QUnit.test("clicking on 'Ok'", async function (assert) {
        const env = await makeDialogTestEnv();
        await mount(ConfirmationDialog, target, {
            env,
            props: {
                body: "Some content",
                title: "Confirmation",
                close: () => {
                    assert.step("Close action");
                },
                confirm: () => {
                    assert.step("Confirm action");
                },
                cancel: () => {
                    throw new Error("should not be called");
                },
            },
        });
        assert.verifySteps([]);
        await click(target, ".modal-footer .btn-primary");
        assert.verifySteps(["Confirm action", "Close action"]);
    });

    QUnit.test("clicking on 'Cancel'", async function (assert) {
        const env = await makeDialogTestEnv();
        await mount(ConfirmationDialog, target, {
            env,
            props: {
                body: "Some content",
                title: "Confirmation",
                close: () => {
                    assert.step("Close action");
                },
                confirm: () => {
                    throw new Error("should not be called");
                },
                cancel: () => {
                    assert.step("Cancel action");
                },
            },
        });
        assert.verifySteps([]);
        await click(target, ".modal-footer .btn-secondary");
        assert.verifySteps(["Cancel action", "Close action"]);
    });

    QUnit.test("can't click twice on 'Ok'", async function (assert) {
        const env = await makeDialogTestEnv();
        await mount(ConfirmationDialog, target, {
            env,
            props: {
                body: "Some content",
                title: "Confirmation",
                close: () => {},
                confirm: () => {
                    assert.step("Confirm");
                },
                cancel: () => {},
            },
        });
        assert.notOk(target.querySelector(".modal-footer .btn-primary").disabled);
        assert.notOk(target.querySelector(".modal-footer .btn-secondary").disabled);
        click(target, ".modal-footer .btn-primary");
        assert.ok(target.querySelector(".modal-footer .btn-primary").disabled);
        assert.ok(target.querySelector(".modal-footer .btn-secondary").disabled);
        assert.verifySteps(["Confirm"]);
    });

    QUnit.test("can't click twice on 'Cancel'", async function (assert) {
        const env = await makeDialogTestEnv();
        await mount(ConfirmationDialog, target, {
            env,
            props: {
                body: "Some content",
                title: "Confirmation",
                close: () => {},
                confirm: () => {},
                cancel: () => {
                    assert.step("Cancel");
                },
            },
        });
        assert.notOk(target.querySelector(".modal-footer .btn-primary").disabled);
        assert.notOk(target.querySelector(".modal-footer .btn-secondary").disabled);
        click(target, ".modal-footer .btn-secondary");
        assert.ok(target.querySelector(".modal-footer .btn-primary").disabled);
        assert.ok(target.querySelector(".modal-footer .btn-secondary").disabled);
        assert.verifySteps(["Cancel"]);
    });

    QUnit.test("can't cancel (with escape) after confirm", async function (assert) {
        const def = makeDeferred();
        const env = await makeDialogTestEnv();
        await mount(ConfirmationDialog, target, {
            env,
            props: {
                body: "Some content",
                title: "Confirmation",
                close: () => {
                    assert.step("close");
                },
                confirm: () => {
                    assert.step("confirm");
                    return def;
                },
                cancel: () => {
                    throw new Error("should not cancel");
                },
            },
        });
        await click(target, ".modal-footer .btn-primary");
        assert.verifySteps(["confirm"]);
        triggerHotkey("escape");
        await nextTick();
        assert.verifySteps([]);
        def.resolve();
        await nextTick();
        assert.verifySteps(["close"]);
    });

    QUnit.test("wait for confirm callback before closing", async function (assert) {
        const env = await makeDialogTestEnv();
        const def = makeDeferred();
        await mount(ConfirmationDialog, target, {
            env,
            props: {
                body: "Some content",
                title: "Confirmation",
                close: () => {
                    assert.step("close");
                },
                confirm: () => {
                    assert.step("confirm");
                    return def;
                },
            },
        });
        await click(target, ".modal-footer .btn-primary");
        assert.verifySteps(["confirm"]);
        def.resolve();
        await nextTick();
        assert.verifySteps(["close"]);
    });

    QUnit.test("Focus is correctly restored after confirmation", async function (assert) {
        const env = await makeDialogTestEnv();

        class MyComp extends Component {}
        MyComp.template = xml`<div class="my-comp"><input type="text" class="my-input"/></div>`;

        await mount(MyComp, target, { env });
        target.querySelector(".my-input").focus();
        assert.strictEqual(document.activeElement, target.querySelector(".my-input"));

        const comp = await mount(ConfirmationDialog, target, {
            env,
            props: {
                body: "Some content",
                title: "Confirmation",
                confirm: () => {},
                close: () => {},
            },
        });
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".modal-footer .btn-primary")
        );
        await click(target, ".modal-footer .btn-primary");
        assert.strictEqual(
            document.activeElement,
            document.body,
            "As the button is disabled, the focus is now on the body"
        );
        destroy(comp);
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".my-input"),
            "After destruction of the dialog, the focus is restored to the input"
        );
    });
});
