/** @odoo-module **/

import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeTestEnv } from "../helpers/mock_env";
import { click, getFixture, mount, triggerHotkey } from "../helpers/utils";
import { makeFakeDialogService } from "../helpers/mock_services";

const serviceRegistry = registry.category("services");
let target;

async function makeDialogTestEnv() {
    const env = await makeTestEnv();
    env.dialogData = {
        isActive: true,
        close: () => {},
    };
    return env;
}

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
        assert.expect(4);

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
                }
            }
        });
        assert.verifySteps([]);
        triggerHotkey("escape");
        assert.verifySteps([
            "Cancel action",
            "Close action"
        ], "dialog has called its cancel method before its closure");
    });

    QUnit.test("clicking on dialog buttons", async function (assert) {
        assert.expect(7);

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
                    assert.step("Cancel action");
                }
            }
        });
        assert.verifySteps([]);
        await click(target, ".modal-footer .btn-primary");
        assert.verifySteps([
            "Confirm action",
            "Close action"
        ]);
        await click(target, ".modal-footer .btn-secondary");
        assert.verifySteps([
            "Cancel action",
            "Close action"
        ], "dialog has called its cancel method before its closure");
    });
});
