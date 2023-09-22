/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { calendarNotificationService } from "@calendar/js/services/calendar_notification_service";

import { start } from "@mail/../tests/helpers/test_utils";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

const serviceRegistry = registry.category("services");

QUnit.module("Calendar Notification", (hooks) => {
    hooks.beforeEach(() => {
        serviceRegistry.add("calendarNotification", calendarNotificationService);
        patchWithCleanup(browser, {
            setTimeout(fn) {
                super.setTimeout(fn, 0);
            },
        });
    });

    QUnit.test(
        "can listen on bus and display notifications in DOM and click OK",
        async (assert) => {
            const pyEnv = await startServer();
            const mockRPC = (route, args) => {
                if (route === "/calendar/notify") {
                    return Promise.resolve([]);
                }
                if (route === "/calendar/notify_ack") {
                    assert.step("notifyAck");
                    return Promise.resolve(true);
                }
            };
            await start({ mockRPC });
            pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "calendar.alarm", [
                {
                    alarm_id: 1,
                    event_id: 2,
                    title: "Meeting",
                    message: "Very old meeting message",
                    timer: 20 * 60,
                    notify_at: "1978-04-14 12:45:00",
                },
            ]);
            await contains(".o_notification", { text: "Very old meeting message" });
            await click(".o_notification_buttons button", { text: "OK" });
            await contains(".o_notification", { count: 0 });
            assert.verifySteps(["notifyAck"]);
        }
    );

    QUnit.test(
        "can listen on bus and display notifications in DOM and click Detail",
        async (assert) => {
            const pyEnv = await startServer();
            const mockRPC = (route, args) => {
                if (route === "/calendar/notify") {
                    return Promise.resolve([]);
                }
            };
            const fakeActionService = {
                name: "action",
                start() {
                    return {
                        doAction(actionId) {
                            assert.step(actionId.type);
                            return Promise.resolve(true);
                        },
                        loadState(state, options) {
                            return Promise.resolve(true);
                        },
                    };
                },
            };
            serviceRegistry.add("action", fakeActionService, { force: true });
            await start({ mockRPC });
            pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "calendar.alarm", [
                {
                    alarm_id: 1,
                    event_id: 2,
                    title: "Meeting",
                    message: "Very old meeting message",
                    timer: 20 * 60,
                    notify_at: "1978-04-14 12:45:00",
                },
            ]);
            await contains(".o_notification", { text: "Very old meeting message" });
            await click(".o_notification_buttons button", { text: "Details" });
            await contains(".o_notification", { count: 0 });
            assert.verifySteps(["ir.actions.act_window"]);
        }
    );

    QUnit.test(
        "can listen on bus and display notifications in DOM and click Snooze",
        async (assert) => {
            const pyEnv = await startServer();
            const mockRPC = (route, args) => {
                if (route === "/calendar/notify") {
                    return Promise.resolve([]);
                }
                if (route === "/calendar/notify_ack") {
                    assert.step("notifyAck");
                    return Promise.resolve(true);
                }
            };
            await start({ mockRPC });
            pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "calendar.alarm", [
                {
                    alarm_id: 1,
                    event_id: 2,
                    title: "Meeting",
                    message: "Very old meeting message",
                    timer: 20 * 60,
                    notify_at: "1978-04-14 12:45:00",
                },
            ]);
            await contains(".o_notification", { text: "Very old meeting message" });
            await click(".o_notification button", { text: "Snooze" });
            await contains(".o_notification", { count: 0 });
            assert.verifySteps([], "should only close the notification withtout calling a rpc");
        }
    );
});
