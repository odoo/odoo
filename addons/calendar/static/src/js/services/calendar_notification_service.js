/** @odoo-module **/

import { serviceRegistry } from "@web/webclient/service_registry";
import { browser } from "@web/core/browser";
import { ConnectionLostError } from "@web/services/rpc_service";

export const calendarNotificationService = {
  async deploy(env) {
    let calendarNotifTimeouts = {};
    let nextCalendarNotifTimeout = null;
    const calendarNotif = {};

    env.bus.on("WEB_CLIENT_READY", null, async () => {
      const legacyEnv = owl.Component.env;
      legacyEnv.services.bus_service.onNotification(this, (notifications) => {
        for (const notif of notifications) {
          if (notif[0][1] === "calendar.alarm") {
            displayCalendarNotification(notif[1]);
          }
        }
      });
      legacyEnv.services.bus_service.startPolling();
    });

    /**
     * Displays the Calendar notification on user's screen
     */
    function displayCalendarNotification(notifications) {
      let lastNotifTimer = 0;

      // Clear previously set timeouts and destroy currently displayed calendar notifications
      browser.clearTimeout(nextCalendarNotifTimeout);
      Object.values(calendarNotifTimeouts).forEach((notif) =>
        browser.clearTimeout(notif)
      );
      calendarNotifTimeouts = {};

      // For each notification, set a timeout to display it
      notifications.forEach(function (notif) {
        const key = notif.event_id + "," + notif.alarm_id;
        if (key in calendarNotif) {
          return;
        }
        calendarNotifTimeouts[key] = browser.setTimeout(function () {
          const notificationID = env.services.notification.create(
            notif.message,
            {
              title: notif.title,
              type: "warning",
              sticky: true,
              onClose: () => {
                delete calendarNotif[key];
              },
              buttons: [
                {
                  name: env._t("OK"),
                  primary: true,
                  onClick: async () => {
                    await env.services.rpc("/calendar/notify_ack");
                    env.services.notification.close(calendarNotif[key]);
                  },
                },
                {
                  name: env._t("Details"),
                  onClick: async () => {
                    await env.services.action.doAction(
                      "calendar.action_calendar_event_notify",
                      {
                        resId: notif.event_id,
                      }
                    );
                    env.services.notification.close(calendarNotif[key]);
                  },
                },
                {
                  name: env._t("Snooze"),
                  onClick: () => {
                    env.services.notification.close(calendarNotif[key]);
                  },
                },
              ],
            }
          );
          calendarNotif[key] = notificationID;
        }, notif.timer * 1000);
        lastNotifTimer = Math.max(lastNotifTimer, notif.timer);
      });

      // Set a timeout to get the next notifications when the last one has been displayed
      if (lastNotifTimer > 0) {
        nextCalendarNotifTimeout = browser.setTimeout(
          getNextCalendarNotif,
          lastNotifTimer * 1000
        );
      }
    }

    async function getNextCalendarNotif() {
      try {
        const result = await env.services.rpc(
          "/calendar/notify",
          {},
          { shadow: true }
        );
        displayCalendarNotification(result);
      } catch (error) {
        if (!(error instanceof ConnectionLostError)) {
          throw error;
        }
      }
    }
  },
};

serviceRegistry.add("calendarNotification", calendarNotificationService);
