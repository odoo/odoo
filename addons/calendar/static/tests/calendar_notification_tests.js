/** @odoo-module */

import * as legacyRegistry from "web.Registry";
import * as BusService from "bus.BusService";
import * as RamStorage from "web.RamStorage";
import * as AbstractStorageService from "web.AbstractStorageService";

import {
  createWebClient,
  getActionManagerTestConfig,
} from "@web/../tests/actions/helpers";
import { calendarNotificationService } from "@calendar/js/services/calendar_notification_service";
import { click, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { NotificationContainer } from "@web/notifications/notification_container";
import { Registry } from "@web/core/registry";
import { browser } from "@web/core/browser";

const LocalStorageService = AbstractStorageService.extend({
  storage: new RamStorage(),
});

QUnit.module("Calendar Notification", (hooks) => {
  let legacyServicesRegistry;
  let testConfig;
  hooks.beforeEach(() => {
    legacyServicesRegistry = new legacyRegistry();
    legacyServicesRegistry.add("bus_service", BusService);
    legacyServicesRegistry.add("local_storage", LocalStorageService);

    testConfig = getActionManagerTestConfig();
    testConfig.serviceRegistry.add(
      "calendarNotification",
      calendarNotificationService
    );

    testConfig.mainComponentRegistry = new Registry();
    testConfig.mainComponentRegistry.add(
      "NotificationContainer",
      NotificationContainer
    );

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
              channel: ["db_name", "calendar.alarm", 7],
              message: [
                {
                  alarm_id: 1,
                  event_id: 2,
                  title: "Meeting",
                  message: "Very old meeting message",
                  timer: 20 * 60,
                  notify_at: "1978-04-14 12:45:00",
                },
              ],
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
        testConfig,
        legacyParams: { serviceRegistry: legacyServicesRegistry },
        mockRPC,
      });

      await nextTick();

      assert.containsOnce(webClient.el, ".o_notification_body");
      assert.strictEqual(
        webClient.el.querySelector(
          ".o_notification_body .o_notification_content"
        ).textContent,
        "Very old meeting message"
      );

      await click(webClient.el.querySelector(".o_notification_buttons .btn"));
      assert.verifySteps(["notifyAck"]);
      assert.containsNone(webClient.el, ".o_notification");

      webClient.destroy();
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
              channel: ["db_name", "calendar.alarm", 7],
              message: [
                {
                  alarm_id: 1,
                  event_id: 2,
                  title: "Meeting",
                  message: "Very old meeting message",
                  timer: 20 * 60,
                  notify_at: "1978-04-14 12:45:00",
                },
              ],
            },
          ]);
        }
        if (route === "/calendar/notify") {
          return Promise.resolve([]);
        }
      };

      const fakeActionService = {
        name: "action",
        deploy() {
          return {
            doAction(actionId) {
              assert.step(actionId);
              return Promise.resolve(true);
            },
            loadState(state, options) {
              return Promise.resolve(true);
            },
          };
        },
      };
      testConfig.serviceRegistry.remove("action");
      testConfig.serviceRegistry.add("action", fakeActionService);

      const webClient = await createWebClient({
        testConfig,
        legacyParams: { serviceRegistry: legacyServicesRegistry },
        mockRPC,
      });

      await nextTick();

      assert.containsOnce(webClient.el, ".o_notification_body");
      assert.strictEqual(
        webClient.el.querySelector(
          ".o_notification_body .o_notification_content"
        ).textContent,
        "Very old meeting message"
      );

      await click(
        webClient.el.querySelectorAll(".o_notification_buttons .btn")[1]
      );
      assert.verifySteps(["calendar.action_calendar_event_notify"]);
      assert.containsNone(webClient.el, ".o_notification");

      webClient.destroy();
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
              id: "prout",
              channel: ["db_name", "calendar.alarm", 7],
              message: [
                {
                  alarm_id: 1,
                  event_id: 2,
                  title: "Meeting",
                  message: "Very old meeting message",
                  timer: 20 * 60,
                  notify_at: "1978-04-14 12:45:00",
                },
              ],
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
        testConfig,
        legacyParams: { serviceRegistry: legacyServicesRegistry },
        mockRPC,
      });

      await nextTick();

      assert.containsOnce(webClient.el, ".o_notification_body");
      assert.strictEqual(
        webClient.el.querySelector(
          ".o_notification_body .o_notification_content"
        ).textContent,
        "Very old meeting message"
      );

      await click(
        webClient.el.querySelectorAll(".o_notification_buttons .btn")[2]
      );
      assert.verifySteps(
        [],
        "should only close the notification withtout calling a rpc"
      );
      assert.containsNone(webClient.el, ".o_notification");

      webClient.destroy();
    }
  );
});
