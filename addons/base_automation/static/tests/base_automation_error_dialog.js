/** @odoo-modules */

import session from "web.session";
import { registry } from "@web/core/registry";
import { errorService } from "@web/core/errors/error_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { uiService } from "@web/core/ui_service";
import { hotkeyService } from "@web/webclient/hotkeys/hotkey_service";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeRPCService, makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { RPCError } from "@web/core/network/rpc_service";

import { BaseAutomationErrorDialog } from "../src/js/base_automation_error_dialog";

const serviceRegistry = registry.category("services");

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
            const windowAddEventListener = window.addEventListener;
            window.addEventListener = (type, cb) => {
                if (type === "unhandledrejection") {
                    unhandledRejectionCb = cb;
                }
            };
            registerCleanup(() => {
                window.addEventListener = windowAddEventListener;
            });
        },
    });

    QUnit.test("Error due to an automated action", async function (assert) {
        assert.expect(4);

        const error = new RPCError();
        const errorContext = {
            exception_class: "base_automation",
            base_automation: {
                id: 1,
                name: "Test base automation error dialog",
            },
        };
        Object.assign(error, {
            subType: "Odoo Client Error",
            message: "Message",
            data: {
                debug: "Traceback",
                context: errorContext,
            },
            exceptionName: errorContext.exception_class,
        });

        const env = await makeTestEnv();
        const dialogOpened = new Promise((resolve) => {
            env.services.dialog.bus.on("ADD", null, async ({ class: dialogClass, props }) => {
                assert.equal(props.data.context, errorContext, "Received the correct error context");
                const fixture = document.getElementById("qunit-fixture");
                const dialogContainer = document.createElement('div');
                dialogContainer.classList.add('o_dialog_container');
                fixture.appendChild(dialogContainer);
                await owl.mount(dialogClass, { target: fixture, props, env });
                assert.containsOnce(dialogContainer, '.modal .fa-clipboard');
                assert.containsOnce(dialogContainer, '.modal .o_disable_action_button');
                assert.containsOnce(dialogContainer, '.modal .o_edit_action_button');
                resolve();
            });
        });
        const errorEvent = new PromiseRejectionEvent("error", { reason: {
            message: error,
            legacy: true,
            event: $.Event(),
        }, promise: null });
        await unhandledRejectionCb(errorEvent);
        await dialogOpened;
    });

    QUnit.test("Error not due to an automated action", async function (assert) {
        assert.expect(3);

        const error = new RPCError();
        Object.assign(error, {
            subType: "Odoo Client Error",
            message: "Message",
            data: {
                debug: "Traceback",
            },
        });

        const env = await makeTestEnv();
        const dialogOpened = new Promise((resolve) => {
            env.services.dialog.bus.on("ADD", null, async ({ class: dialogClass, props }) => {
                const fixture = document.getElementById("qunit-fixture");
                const dialogContainer = document.createElement('div');
                dialogContainer.classList.add('o_dialog_container');
                fixture.appendChild(dialogContainer);
                await owl.mount(dialogClass, { target: fixture, props, env });
                assert.containsOnce(dialogContainer, '.modal .fa-clipboard');
                assert.containsNone(dialogContainer, '.modal .o_disable_action_button');
                assert.containsNone(dialogContainer, '.modal .o_edit_action_button');
                resolve();
            });
        });
        const errorEvent = new PromiseRejectionEvent("error", { reason: {
            message: error,
            legacy: true,
            event: $.Event(),
        }, promise: null });
        await unhandledRejectionCb(errorEvent);
        await dialogOpened;
    });

});
