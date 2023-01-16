/** @odoo-module */

import * as legacyRegistry from "web.Registry";
import * as BusService from "bus.BusService";
import * as RamStorage from "web.RamStorage";
import * as AbstractStorageService from "web.AbstractStorageService";

import { createWebClient } from "@web/../tests/webclient/helpers";
import { calendarNotificationService } from "@calendar/js/services/calendar_notification_service";
import { click, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

const LocalStorageService = AbstractStorageService.extend({
    storage: new RamStorage(),
});
const serviceRegistry = registry.category("services");

QUnit.module("Calendar Notification", (hooks) => {
    let legacyServicesRegistry;
    hooks.beforeEach(() => {
        legacyServicesRegistry = new legacyRegistry();
        legacyServicesRegistry.add("bus_service", BusService);
        legacyServicesRegistry.add("local_storage", LocalStorageService);

        serviceRegistry.add("calendarNotification", calendarNotificationService);

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
    });

    QUnit.test(
        "can listen on bus and display notifications in DOM and click OK",
        async (assert) => {
            assert.expect(5);

            let pollNumber = 0;
            const mockRPC = (route, args) => {
                if (route === "/longpolling/poll") {
                    if (pollNumber > 0) {
                        return new Promise(() => {}); // let it hang to avoid further calls
                    }
                    pollNumber++;
                    return Promise.resolve([
                        {
                            id: "prout",
                            message: {
                                type: "calendar.alarm",
                                payload: [{
                                    alarm_id: 1,
                                    event_id: 2,
                                    title: "Meeting",
                                    message: "Very old meeting message",
                                    timer: 20 * 60,
                                    notify_at: "1978-04-14 12:45:00",
                                }],
                            },
                        },
                    ]);
                }
                if (route === "/calendar/notify") {
                    return Promise.resolve([]);
                }
                if (route === "/calendar/notify_ack") {
                    assert.step("notifyAck");
                    return Promise.resolve(true);
                }
            };

            const webClient = await createWebClient({
                legacyParams: { serviceRegistry: legacyServicesRegistry },
                mockRPC,
            });

            await nextTick();

            assert.containsOnce(webClient.el, ".o_notification_body");
            assert.strictEqual(
                webClient.el.querySelector(".o_notification_body .o_notification_content")
                    .textContent,
                "Very old meeting message"
            );

            await click(webClient.el.querySelector(".o_notification_buttons .btn"));
            assert.verifySteps(["notifyAck"]);
            assert.containsNone(webClient.el, ".o_notification");
        }
    );

    QUnit.test(
        "can listen on bus and display notifications in DOM and click Detail",
        async (assert) => {
            assert.expect(5);

            let pollNumber = 0;
            const mockRPC = (route, args) => {
                if (route === "/longpolling/poll") {
                    if (pollNumber > 0) {
                        return new Promise(() => {}); // let it hang to avoid further calls
                    }
                    pollNumber++;
                    return Promise.resolve([
                        {
                            id: "prout",
                            message: {
                                type: "calendar.alarm",
                                payload: [{
                                    alarm_id: 1,
                                    event_id: 2,
                                    title: "Meeting",
                                    message: "Very old meeting message",
                                    timer: 20 * 60,
                                    notify_at: "1978-04-14 12:45:00",
                                }],
                            },
                        },
                    ]);
                }
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

            const webClient = await createWebClient({
                legacyParams: { serviceRegistry: legacyServicesRegistry },
                mockRPC,
            });

            await nextTick();

            assert.containsOnce(webClient.el, ".o_notification_body");
            assert.strictEqual(
                webClient.el.querySelector(".o_notification_body .o_notification_content")
                    .textContent,
                "Very old meeting message"
            );

            await click(webClient.el.querySelectorAll(".o_notification_buttons .btn")[1]);
            assert.verifySteps(["ir.actions.act_window"]);
            assert.containsNone(webClient.el, ".o_notification");
        }
    );

    QUnit.test(
        "can listen on bus and display notifications in DOM and click Snooze",
        async (assert) => {
            assert.expect(4);

            let pollNumber = 0;
            const mockRPC = (route, args) => {
                if (route === "/longpolling/poll") {
                    if (pollNumber > 0) {
                        return new Promise(() => {}); // let it hang to avoid further calls
                    }
                    pollNumber++;
                    return Promise.resolve([
                        {
                            message: {
                                id: "prout",
                                type: "calendar.alarm",
                                payload: [{
                                    alarm_id: 1,
                                    event_id: 2,
                                    title: "Meeting",
                                    message: "Very old meeting message",
                                    timer: 20 * 60,
                                    notify_at: "1978-04-14 12:45:00",
                                }],
                            },
                        },
                    ]);
                }
                if (route === "/calendar/notify") {
                    return Promise.resolve([]);
                }
                if (route === "/calendar/notify_ack") {
                    assert.step("notifyAck");
                    return Promise.resolve(true);
                }
            };

            const webClient = await createWebClient({
                legacyParams: { serviceRegistry: legacyServicesRegistry },
                mockRPC,
            });

            await nextTick();

            assert.containsOnce(webClient.el, ".o_notification_body");
            assert.strictEqual(
                webClient.el.querySelector(".o_notification_body .o_notification_content")
                    .textContent,
                "Very old meeting message"
            );

            await click(webClient.el.querySelectorAll(".o_notification_buttons .btn")[2]);
            assert.verifySteps([], "should only close the notification withtout calling a rpc");
            assert.containsNone(webClient.el, ".o_notification");
        }
    );
});
