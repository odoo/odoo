/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import AbstractAction from "web.AbstractAction";
import core from "web.core";
import * as LegacyRegistry from "web.Registry";
import { registerCleanup } from "../../helpers/cleanup";
import { nextTick, patchWithCleanup } from "../../helpers/utils";
import { createWebClient, doAction } from "../../webclient/helpers";

let legacyParams;

QUnit.module("Service Provider Adapter Notification", (hooks) => {
  hooks.beforeEach(() => {
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
      patchWithCleanup(browser, {
        setTimeout: (cb, delay) => {
            if (!delay) {
                return; // Timeouts from router service
            }
            timeoutCB = cb;
            assert.step("time: " + delay);
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
      const webClient = await createWebClient({ legacyParams });
      await doAction(webClient, "NotifyTestLeg");
      await nextTick();
      assert.containsOnce(document.body, ".o_notification");
      const notif = document.body.querySelector(".o_notification");
      assert.strictEqual(notif.querySelector(".o_notification_title").textContent, "Some title");
      assert.strictEqual(
        notif.querySelector(".o_notification_content").textContent,
        "I'm a danger notification"
      );
      assert.hasClass(notif, "border-danger");

      //Close the notification
      await doAction(webClient, "CloseTestLeg");
      await nextTick();
      assert.containsOnce(document.body, ".o_notification");
      // simulate end of timeout
      timeoutCB();
      await nextTick();
      assert.containsNone(document.body, ".o_notification");
      assert.verifySteps(["time: 3000"]);
    }
  );
});
