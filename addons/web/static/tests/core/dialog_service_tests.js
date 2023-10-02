/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { ErrorDialog } from "@web/core/errors/error_dialogs";
import { errorService } from "@web/core/errors/error_service";
import { registry } from "@web/core/registry";
import { notificationService } from "@web/core/notifications/notification_service";
import { uiService } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { clearRegistryWithCleanup, makeTestEnv } from "../helpers/mock_env";
import { makeFakeLocalizationService, makeFakeRPCService } from "../helpers/mock_services";
import {
    click,
    getFixture,
    makeDeferred,
    mount,
    nextTick,
    patchWithCleanup,
} from "../helpers/utils";
import { Dialog } from "../../src/core/dialog/dialog";

import { Component, onMounted, xml } from "@odoo/owl";

let env;
let target;
const serviceRegistry = registry.category("services");
const mainComponentRegistry = registry.category("main_components");

class PseudoWebClient extends Component {
    setup() {
        this.Components = mainComponentRegistry.getEntries();
    }
}
PseudoWebClient.template = xml`
        <div>
            <div>
                <t t-foreach="Components" t-as="C" t-key="C[0]">
                    <t t-component="C[1].Component" t-props="C[1].props"/>
                </t>
            </div>
        </div>
    `;

QUnit.module("DialogManager", {
    async beforeEach() {
        target = getFixture();
        clearRegistryWithCleanup(mainComponentRegistry);
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("l10n", makeFakeLocalizationService());

        env = await makeTestEnv();
    },
});
QUnit.test("Simple rendering with a single dialog", async (assert) => {
    assert.expect(4);
    class CustomDialog extends Component {}
    CustomDialog.components = { Dialog };
    CustomDialog.template = xml`<Dialog title="'Welcome'">content</Dialog>`;
    await mount(PseudoWebClient, target, { env });
    assert.containsNone(target, ".o_dialog");
    env.services.dialog.add(CustomDialog);
    await nextTick();
    assert.containsOnce(target, ".o_dialog");
    assert.strictEqual(target.querySelector("header .modal-title").textContent, "Welcome");
    await click(target.querySelector(".o_dialog footer button"));
    assert.containsNone(target, ".o_dialog");
});

QUnit.test("Simple rendering and close a single dialog", async (assert) => {
    assert.expect(4);

    class CustomDialog extends Component {}
    CustomDialog.components = { Dialog };
    CustomDialog.template = xml`<Dialog title="'Welcome'">content</Dialog>`;

    await mount(PseudoWebClient, target, { env });
    assert.containsNone(target, ".o_dialog");

    const removeDialog = env.services.dialog.add(CustomDialog);
    await nextTick();
    assert.containsOnce(target, ".o_dialog");
    assert.strictEqual(target.querySelector("header .modal-title").textContent, "Welcome");

    removeDialog();
    await nextTick();
    assert.containsNone(target, ".o_dialog");

    // Call a second time, the close on the dialog.
    // As the dialog is already close, this call is just ignored. No error should be raised.
    removeDialog();
    await nextTick();
});

QUnit.test("rendering with two dialogs", async (assert) => {
    assert.expect(7);
    class CustomDialog extends Component {}
    CustomDialog.components = { Dialog };
    CustomDialog.template = xml`<Dialog title="props.title">content</Dialog>`;

    await mount(PseudoWebClient, target, { env });
    assert.containsNone(target, ".o_dialog");
    env.services.dialog.add(CustomDialog, { title: "Hello" });
    await nextTick();
    assert.containsOnce(target, ".o_dialog");
    assert.strictEqual(target.querySelector("header .modal-title").textContent, "Hello");
    env.services.dialog.add(CustomDialog, { title: "Sauron" });
    await nextTick();
    assert.containsN(target, ".o_dialog", 2);
    assert.deepEqual(
        [...target.querySelectorAll("header .modal-title")].map((el) => el.textContent),
        ["Hello", "Sauron"]
    );
    await click(target.querySelector(".o_dialog footer button"));
    assert.containsOnce(target, ".o_dialog");
    assert.strictEqual(target.querySelector("header .modal-title").textContent, "Sauron");
});

QUnit.test("multiple dialogs can become the UI active element", async (assert) => {
    assert.expect(3);
    class CustomDialog extends Component {}
    CustomDialog.components = { Dialog };
    CustomDialog.template = xml`<Dialog title="props.title">content</Dialog>`;
    await mount(PseudoWebClient, target, { env });

    env.services.dialog.add(CustomDialog, { title: "Hello" });
    await nextTick();
    let dialogModal = target.querySelector(".o_dialog:not(.o_inactive_modal) .modal");

    assert.strictEqual(dialogModal, env.services.ui.activeElement);

    env.services.dialog.add(CustomDialog, { title: "Sauron" });
    await nextTick();
    dialogModal = target.querySelector(".o_dialog:not(.o_inactive_modal) .modal");

    assert.strictEqual(dialogModal, env.services.ui.activeElement);

    env.services.dialog.add(CustomDialog, { title: "Rafiki" });
    await nextTick();
    dialogModal = target.querySelector(".o_dialog:not(.o_inactive_modal) .modal");

    assert.strictEqual(dialogModal, env.services.ui.activeElement);
});

QUnit.test("Interactions between multiple dialogs", async (assert) => {
    assert.expect(10);
    function activity(modals) {
        const active = [];
        const names = [];
        for (let i = 0; i < modals.length; i++) {
            active[i] = !modals[i].classList.contains("o_inactive_modal");
            names[i] = modals[i].querySelector(".modal-title").textContent;
        }
        return { active, names };
    }

    class CustomDialog extends Component {}
    CustomDialog.components = { Dialog };
    CustomDialog.template = xml`<Dialog title="props.title">content</Dialog>`;
    await mount(PseudoWebClient, target, { env });

    env.services.dialog.add(CustomDialog, { title: "Hello" });
    await nextTick();
    env.services.dialog.add(CustomDialog, { title: "Sauron" });
    await nextTick();
    env.services.dialog.add(CustomDialog, { title: "Rafiki" });
    await nextTick();

    let modals = document.querySelectorAll(".o_dialog");
    assert.containsN(target, ".o_dialog", 3);
    let res = activity(modals);
    assert.deepEqual(res.active, [false, false, true]);
    assert.deepEqual(res.names, ["Hello", "Sauron", "Rafiki"]);

    let lastDialog = modals[modals.length - 1];
    lastDialog.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Escape" }));
    await nextTick();
    modals = document.querySelectorAll(".o_dialog");
    assert.containsN(target, ".o_dialog", 2);
    res = activity(modals);
    assert.deepEqual(res.active, [false, true]);
    assert.deepEqual(res.names, ["Hello", "Sauron"]);

    lastDialog = modals[modals.length - 1];
    await click(lastDialog, "footer button");
    modals = document.querySelectorAll(".o_dialog");
    assert.containsN(target, ".o_dialog", 1);
    res = activity(modals);
    assert.deepEqual(res.active, [true]);
    assert.deepEqual(res.names, ["Hello"]);

    lastDialog = modals[modals.length - 1];
    await click(lastDialog, "footer button");
    assert.containsNone(target, ".o_dialog");
});

QUnit.test("dialog component crashes", async (assert) => {
    assert.expect(3);
    assert.expectErrors();

    class FailingDialog extends Component {
        setup() {
            throw new Error("Some Error");
        }
    }
    FailingDialog.components = { Dialog };
    FailingDialog.template = xml`<Dialog title="'Error'">content</Dialog>`;

    const prom = makeDeferred();
    patchWithCleanup(ErrorDialog.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                prom.resolve();
            });
        },
    });

    const rpc = makeFakeRPCService();
    serviceRegistry.add("rpc", rpc, { force: true });
    serviceRegistry.add("notification", notificationService);
    serviceRegistry.add("error", errorService);

    await mount(PseudoWebClient, target, { env });

    env.services.dialog.add(FailingDialog);
    await prom;

    assert.containsOnce(target, ".modal");
    assert.containsOnce(target, ".modal .o_error_dialog");
    assert.verifyErrors(["Some Error"]);
});
