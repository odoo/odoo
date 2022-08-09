/** @odoo-module */

import { busService } from "@bus/services/bus_service";
import { presenceService } from "@bus/services/presence_service";
import { multiTabService } from "@bus/multi_tab_service";
import { getPyEnv } from '@bus/../tests/helpers/mock_python_environment';

import { createWebClient } from "@web/../tests/webclient/helpers";
import { calendarNotificationService } from "@calendar/js/services/calendar_notification_service";
import { click, getFixture, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

QUnit.module("Calendar Notification", (hooks) => {
    let target;
    hooks.beforeEach(() => {
        target = getFixture();

        serviceRegistry.add("calendarNotification", calendarNotificationService);
        serviceRegistry.add("bus_service", busService);
        serviceRegistry.add("presence", presenceService);
        serviceRegistry.add("multi_tab", multiTabService);
        patchWithCleanup(browser, {
            setTimeout(fn) {
                this._super(fn, 0);
            },
        });
    });

    QUnit.test(
        "can listen on bus and display notifications in DOM and click OK",
        async (assert) => {
            assert.expect(5);

            const mockRPC = (route, args) => {
                if (route === "/calendar/notify") {
                    return Promise.resolve([]);
                }
                if (route === "/calendar/notify_ack") {
                    assert.step("notifyAck");
                    return Promise.resolve(true);
                }
            };
            await createWebClient({ mockRPC });
            const pyEnv = await getPyEnv();
            pyEnv['bus.bus']._sendone(pyEnv.currentPartner, "calendar.alarm", [{
                "alarm_id": 1,
                "event_id": 2,
                "title": "Meeting",
                "message": "Very old meeting message",
                "timer": 20 * 60,
                "notify_at": "1978-04-14 12:45:00",
            }]);
            await nextTick();

            assert.containsOnce(target, ".o_notification_body");
            assert.strictEqual(
                target.querySelector(".o_notification_body .o_notification_content")
                    .textContent,
                "Very old meeting message"
            );

            await click(target.querySelector(".o_notification_buttons .btn"));
            assert.verifySteps(["notifyAck"]);
            assert.containsNone(target, ".o_notification");
        }
    );

    QUnit.test(
        "can listen on bus and display notifications in DOM and click Detail",
        async (assert) => {
            assert.expect(5);

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

            await createWebClient({ mockRPC });
            const pyEnv = await getPyEnv();
            pyEnv['bus.bus']._sendone(pyEnv.currentPartner, "calendar.alarm", [{
                "alarm_id": 1,
                "event_id": 2,
                "title": "Meeting",
                "message": "Very old meeting message",
                "timer": 20 * 60,
                "notify_at": "1978-04-14 12:45:00",
            }]);
            await nextTick();

            assert.containsOnce(target, ".o_notification_body");
            assert.strictEqual(
                target.querySelector(".o_notification_body .o_notification_content")
                    .textContent,
                "Very old meeting message"
            );

            await click(target.querySelectorAll(".o_notification_buttons .btn")[1]);
            assert.verifySteps(["ir.actions.act_window"]);
            assert.containsNone(target, ".o_notification");
        }
    );

    QUnit.test(
        "can listen on bus and display notifications in DOM and click Snooze",
        async (assert) => {
            assert.expect(4);

            const mockRPC = (route, args) => {
                if (route === "/calendar/notify") {
                    return Promise.resolve([]);
                }
                if (route === "/calendar/notify_ack") {
                    assert.step("notifyAck");
                    return Promise.resolve(true);
                }
            };

            await createWebClient({ mockRPC });
            const pyEnv = await getPyEnv();
            pyEnv['bus.bus']._sendone(pyEnv.currentPartner, "calendar.alarm", [{
                "alarm_id": 1,
                "event_id": 2,
                "title": "Meeting",
                "message": "Very old meeting message",
                "timer": 20 * 60,
                "notify_at": "1978-04-14 12:45:00",
            }]);
            await nextTick();

            assert.containsOnce(target, ".o_notification_body");
            assert.strictEqual(
                target.querySelector(".o_notification_body .o_notification_content")
                    .textContent,
                "Very old meeting message"
            );

            await click(target.querySelectorAll(".o_notification_buttons .btn")[2]);
            assert.verifySteps([], "should only close the notification withtout calling a rpc");
            assert.containsNone(target, ".o_notification");
        }
    );
});
