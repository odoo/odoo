/** @odoo-module */

import * as legacyRegistry from "web.Registry";
import * as BusService from "bus.BusService";
import * as RamStorage from "web.RamStorage";
import * as AbstractStorageService from "web.AbstractStorageService";

import {
  createWebClient,
  getActionManagerTestConfig,
} from "@web/../tests/actions/helpers";
import { assetsWatchdogService } from "@bus/js/services/assets_watchdog_service";
import { click, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { NotificationContainer } from "@web/notifications/notification_container";
import { Registry } from "@web/core/registry";
import { browser } from "@web/core/browser";

const LocalStorageService = AbstractStorageService.extend({
  storage: new RamStorage(),
});

QUnit.module("Bus Assets WatchDog", (hooks) => {
  let legacyServicesRegistry;
  let testConfig;
  hooks.beforeEach((assert) => {
    legacyServicesRegistry = new legacyRegistry();
    legacyServicesRegistry.add("bus_service", BusService);
    legacyServicesRegistry.add("local_storage", LocalStorageService);

    testConfig = getActionManagerTestConfig();
    testConfig.serviceRegistry.add("assetsWatchdog", assetsWatchdogService);

    testConfig.mainComponentRegistry = new Registry();
    testConfig.mainComponentRegistry.add(
      "NotificationContainer",
      NotificationContainer
    );
    patchWithCleanup(browser, {
      setTimeout: (fn) => fn(),
      clearTimeout: () => {},
      location: {
        reload: () => assert.step("reloadPage"),
      },
    });
  });

  QUnit.test(
    "can listen on bus and displays notifications in DOM",
    async (assert) => {
      assert.expect(5);

      let pollNumber = 0;
      const mockRPC = (route, args) => {
        if (route === "/longpolling/poll") {
          if (pollNumber > 0) {
            return new Promise(() => {}); // let it hang to avoid further calls
          }
          pollNumber++;
          assert.deepEqual(args.channels, ["bundle_changed"]);
          return Promise.resolve([
            {
              id: "prout",
              channel: ["db_name", "bundle_changed"],
              message: ["web.assets_backend", "newHash"],
            },
          ]);
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
        "The page appears to be out of date."
      );

      // reload by clicking on the reload button
      await click(webClient.el, ".o_notification_buttons .btn-primary");
      assert.verifySteps(["reloadPage"]);
      webClient.destroy();
    }
  );
});
