/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { ErrorDialog } from "@web/core/errors/error_dialogs";
import { errorService } from "@web/core/errors/error_service";
import { registry } from "@web/core/registry";
import { notificationService } from "@web/core/notifications/notification_service";
import { uiService } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registerCleanup } from "../helpers/cleanup";
import { clearRegistryWithCleanup, makeTestEnv } from "../helpers/mock_env";
import { makeFakeLocalizationService, makeFakeRPCService } from "../helpers/mock_services";
import { click, getFixture, makeDeferred, nextTick, patchWithCleanup } from "../helpers/utils";
import { Dialog } from "../../src/core/dialog/dialog";

const { Component, mount, tags } = owl;

let env;
let target;
let pseudoWebClient;
const serviceRegistry = registry.category("services");
const mainComponentRegistry = registry.category("main_components");

class PseudoWebClient extends Component {
    setup() {
        this.Components = mainComponentRegistry.getEntries();
    }
}
PseudoWebClient.template = tags.xml`
        <div>
            <div class="o_dialog_container"/>
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
    afterEach() {
        pseudoWebClient.destroy();
    },
});
QUnit.test("Simple rendering with a single dialog", async (assert) => {
    assert.expect(9);
    class CustomDialog extends Dialog {}
    CustomDialog.title = "Welcome";
    pseudoWebClient = await mount(PseudoWebClient, { env, target });
    assert.containsOnce(target, ".o_dialog_manager");
    assert.containsNone(target, ".o_dialog_manager portal");
    assert.containsNone(target, ".o_dialog_container .o_dialog");
    env.services.dialog.open(CustomDialog);
    await nextTick();
    assert.containsOnce(target, ".o_dialog_manager portal");
    assert.containsOnce(target, ".o_dialog_container .o_dialog");
    assert.strictEqual(target.querySelector("header .modal-title").textContent, "Welcome");
    await click(target.querySelector(".o_dialog_container .o_dialog footer button"));
    assert.containsOnce(target, ".o_dialog_manager");
    assert.containsNone(target, ".o_dialog_manager portal");
    assert.containsNone(target, ".o_dialog_container .o_dialog");
});

QUnit.test("Simple rendering and close a single dialog", async (assert) => {
    assert.expect(9);

    class CustomDialog extends Dialog {}
    CustomDialog.title = "Welcome";

    pseudoWebClient = await mount(PseudoWebClient, { env, target });
    assert.containsOnce(target, ".o_dialog_manager");
    assert.containsNone(target, ".o_dialog_manager portal");
    assert.containsNone(target, ".o_dialog_container .o_dialog");

    const dialogId = env.services.dialog.open(CustomDialog);
    await nextTick();
    assert.containsOnce(target, ".o_dialog_manager portal");
    assert.containsOnce(target, ".o_dialog_container .o_dialog");
    assert.strictEqual(target.querySelector("header .modal-title").textContent, "Welcome");

    env.services.dialog.close(dialogId);
    await nextTick();
    assert.containsOnce(target, ".o_dialog_manager");
    assert.containsNone(target, ".o_dialog_manager portal");
    assert.containsNone(target, ".o_dialog_container .o_dialog");

    // Call a second time, the close on the dialog.
    // As the dialog is already close, this call is just ignored. No error should be raised.
    env.services.dialog.close(dialogId);
    await nextTick();
});

QUnit.test("rendering with two dialogs", async (assert) => {
    assert.expect(12);
    class CustomDialog extends Dialog {
        setup() {
            super.setup();
            this.title = this.props.title;
        }
    }
    pseudoWebClient = await mount(PseudoWebClient, { env, target });
    assert.containsOnce(target, ".o_dialog_manager");
    assert.containsNone(target, ".o_dialog_manager portal");
    assert.containsNone(target, ".o_dialog_container .o_dialog");
    env.services.dialog.open(CustomDialog, { title: "Hello" });
    await nextTick();
    assert.containsOnce(target, ".o_dialog_manager portal");
    assert.containsOnce(target, ".o_dialog_container .o_dialog");
    assert.strictEqual(target.querySelector("header .modal-title").textContent, "Hello");
    env.services.dialog.open(CustomDialog, { title: "Sauron" });
    await nextTick();
    assert.containsN(target, ".o_dialog_manager portal", 2);
    assert.containsN(target, ".o_dialog_container .o_dialog", 2);
    assert.deepEqual(
        [...target.querySelectorAll("header .modal-title")].map((el) => el.textContent),
        ["Hello", "Sauron"]
    );
    await click(target.querySelector(".o_dialog_container .o_dialog footer button"));
    assert.containsOnce(target, ".o_dialog_manager portal");
    assert.containsOnce(target, ".o_dialog_container .o_dialog");
    assert.strictEqual(target.querySelector("header .modal-title").textContent, "Sauron");
});

QUnit.test("multiple dialogs can become the UI active element", async (assert) => {
    assert.expect(3);
    class CustomDialog extends Dialog {
        setup() {
            super.setup();
            this.title = this.props.title;
        }
    }
    pseudoWebClient = await mount(PseudoWebClient, { env, target });

    env.services.dialog.open(CustomDialog, { title: "Hello" });
    await nextTick();
    let dialogModal = target.querySelector(
        ".o_dialog_container .o_dialog .modal:not(.o_inactive_modal)"
    );

    assert.strictEqual(dialogModal, env.services.ui.activeElement);

    env.services.dialog.open(CustomDialog, { title: "Sauron" });
    await nextTick();
    dialogModal = target.querySelector(
        ".o_dialog_container .o_dialog .modal:not(.o_inactive_modal)"
    );

    assert.strictEqual(dialogModal, env.services.ui.activeElement);

    env.services.dialog.open(CustomDialog, { title: "Rafiki" });
    await nextTick();
    dialogModal = target.querySelector(
        ".o_dialog_container .o_dialog .modal:not(.o_inactive_modal)"
    );

    assert.strictEqual(dialogModal, env.services.ui.activeElement);
});

QUnit.test("dialog component crashes", async (assert) => {
    assert.expect(4);

    class FailingDialog extends Dialog {
        setup() {
            super.setup();
            throw new Error("Some Error");
        }
    }
    FailingDialog.title = "Error";

    const prom = makeDeferred();
    patchWithCleanup(ErrorDialog.prototype, {
        mounted() {
            this._super();
            prom.resolve();
        },
    });

    const handler = (ev) => {
        assert.step("error");
        // need to preventDefault to remove error from console (so python test pass)
        ev.preventDefault();
    };

    window.addEventListener("unhandledrejection", handler);
    registerCleanup(() => window.removeEventListener("unhandledrejection", handler));
    patchWithCleanup(QUnit, {
        onUnhandledRejection: () => {},
    });

    const rpc = makeFakeRPCService();
    serviceRegistry.add("rpc", rpc);
    serviceRegistry.add("notification", notificationService);
    serviceRegistry.add("error", errorService);
    serviceRegistry.add("localization", makeFakeLocalizationService());

    pseudoWebClient = await mount(PseudoWebClient, { env, target });

    env.services.dialog.open(FailingDialog);
    await prom;
    assert.verifySteps(["error"]);
    assert.containsOnce(pseudoWebClient, ".modal");
    assert.containsOnce(pseudoWebClient, ".modal .o_dialog_error");
});
