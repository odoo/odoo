/** @odoo-modules */

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeServerError } from "@web/../tests/helpers/mock_server";
import {
    makeFakeLocalizationService,
    makeFakeRPCService,
} from "@web/../tests/helpers/mock_services";
import { browser } from "@web/core/browser/browser";
import { dialogService } from "@web/core/dialog/dialog_service";
import { errorService } from "@web/core/errors/error_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { notificationService } from "@web/core/notifications/notification_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { getFixture, mount, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { BaseAutomationErrorDialog } from "@base_automation/base_automation_error_dialog";
import { toRaw } from "@odoo/owl";

const serviceRegistry = registry.category("services");

let target;

QUnit.module("base_automation", {}, function () {
    let unhandledRejectionCb;
    QUnit.module("Error Dialog", {
        async beforeEach() {
            serviceRegistry.add("dialog", dialogService);
            serviceRegistry.add("ui", uiService);
            serviceRegistry.add("error", errorService);
            serviceRegistry.add("hotkey", hotkeyService);
            serviceRegistry.add("localization", makeFakeLocalizationService());
            serviceRegistry.add("action", { start: () => {} });
            serviceRegistry.add("orm", { start: () => {} });
            serviceRegistry.add("user", { start: () => ({ isAdmin: true }) });
            registry.category("error_dialogs").add("base_automation", BaseAutomationErrorDialog);
            // Both of these are unused but required for the error service to call error handlers
            serviceRegistry.add("notification", notificationService);
            serviceRegistry.add("rpc", makeFakeRPCService());
            const windowAddEventListener = browser.addEventListener;
            browser.addEventListener = (type, cb) => {
                if (type === "unhandledrejection") {
                    unhandledRejectionCb = cb;
                }
            };
            registerCleanup(() => {
                browser.addEventListener = windowAddEventListener;
            });
            target = getFixture();
        },
    });

    QUnit.test("Error due to an automation rule", async function (assert) {
        assert.expect(4);

        const errorContext = {
            exception_class: "base_automation",
            base_automation: {
                id: 1,
                name: "Test base automation error dialog",
            },
        };

        const error = makeServerError({
            subType: "Odoo Client Error",
            message: "Message",
            context: errorContext,
        });

        patchWithCleanup(BaseAutomationErrorDialog.prototype, {
            setup() {
                assert.equal(
                    toRaw(this.props.data.context),
                    errorContext,
                    "Received the correct error context"
                );
                super.setup();
            },
        });

        const env = await makeTestEnv();
        await mount(MainComponentsContainer, target, { env });

        const errorEvent = new PromiseRejectionEvent("error", {
            reason: error,
            promise: null,
            cancelable: true,
            bubbles: true,
        });
        await unhandledRejectionCb(errorEvent);
        await nextTick();
        assert.containsOnce(target, ".modal .fa-clipboard");
        assert.containsOnce(target, ".modal .o_disable_action_button");
        assert.containsOnce(target, ".modal .o_edit_action_button");
    });

    QUnit.test("Error not due to an automation rule", async function (assert) {
        assert.expect(3);

        const error = makeServerError({
            subType: "Odoo Client Error",
            message: "Message",
        });

        const env = await makeTestEnv();
        await mount(MainComponentsContainer, target, { env });

        const errorEvent = new PromiseRejectionEvent("error", {
            reason: error,
            promise: null,
            cancelable: true,
            bubbles: true,
        });
        await unhandledRejectionCb(errorEvent);
        await nextTick();
        assert.containsOnce(target, ".modal .fa-clipboard");
        assert.containsNone(target, ".modal .o_disable_action_button");
        assert.containsNone(target, ".modal .o_edit_action_button");
    });
});
