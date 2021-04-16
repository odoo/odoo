/** @odoo-module **/
import { getLegacy } from "web.test_legacy";
import { createWebClient, doAction, getActionManagerTestConfig } from "../../actions/helpers";
import { actionRegistry } from "../../../src/actions/action_registry";
import { registerCleanup } from "../../helpers/cleanup";
import { Registry } from "@web/core/registry";
import { NotificationContainer } from "@web/notifications/notification_container";
import * as LegacyRegistry from "web.Registry";
import { nextTick } from "../../helpers/utils";
import { patch, unpatch } from "../../../src/utils/patch";
import { browser } from "../../../src/core/browser";

let testConfig;
let AbstractAction;
let core;
let legacyParams;

QUnit.module("Service Provider Adapter Notification", (hooks) => {
  hooks.before(() => {
    const legacy = getLegacy();
    AbstractAction = legacy.AbstractAction;
    core = legacy.core;
  });

  const owner = Symbol("owner");

  hooks.beforeEach(() => {
    actionRegistry.on("UPDATE", owner, (payload) => {
      if (payload.operation === "add" && testConfig.actionRegistry) {
        testConfig.actionRegistry.add(payload.key, payload.value);
      }
    });
  });
  hooks.afterEach(() => {
    actionRegistry.off("UPDATE", owner);
  });
  hooks.beforeEach(() => {
    testConfig = getActionManagerTestConfig();
    testConfig.mainComponentRegistry = new Registry();
    testConfig.mainComponentRegistry.add("NotificationContainer", NotificationContainer);
    legacyParams = {
      serviceRegistry: new LegacyRegistry(),
    };
  });

  QUnit.test(
    "can display and close a sticky danger notification with a title (legacy)",
    async function (assert) {
      assert.expect(8);
      let notifId;
      let timeoutCB;
      patch(browser, "mock.settimeout.cb", {
        setTimeout: (cb, t) => {
          timeoutCB = cb;
          assert.step("time: " + t);
          return 1;
        },
      });
      const NotifyAction = AbstractAction.extend({
        on_attach_callback() {
          notifId = this.call("notification", "notify", {
            title: "Some title",
            message: "I'm a danger notification",
            type: "danger",
            sticky: true,
          });
        },
      });
      const CloseAction = AbstractAction.extend({
        on_attach_callback() {
          this.call("notification", "close", notifId, false, 3000);
        },
      });
      core.action_registry.add("NotifyTestLeg", NotifyAction);
      core.action_registry.add("CloseTestLeg", CloseAction);
      registerCleanup(() => {
        delete core.action_registry.map.NotifyTestLeg;
        delete core.action_registry.map.CloseTestLeg;
      });
      const webClient = await createWebClient({ testConfig, legacyParams });
      await doAction(webClient, "NotifyTestLeg");
      await nextTick();
      assert.containsOnce(document.body, ".o_notification");
      const notif = document.body.querySelector(".o_notification");
      assert.strictEqual(notif.querySelector(".o_notification_title").textContent, "Some title");
      assert.strictEqual(
        notif.querySelector(".o_notification_content").textContent,
        "I'm a danger notification"
      );
      assert.hasClass(notif, "bg-danger");

      //Close the notification
      await doAction(webClient, "CloseTestLeg");
      await nextTick();
      assert.containsOnce(document.body, ".o_notification");
      // simulate end of timeout
      timeoutCB();
      await nextTick();
      assert.containsNone(document.body, ".o_notification");
      assert.verifySteps(["time: 3000"]);
      unpatch(browser, "mock.settimeout.cb");
    }
  );
});
