/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { ConnectionLostError } from "@web/core/network/rpc_service";
import { registry } from "@web/core/registry";

export const calendarNotificationService = {
    dependencies: ["action", "bus_service", "notification", "rpc"],

    start(env, { action, bus_service, notification, rpc }) {
        let calendarNotifTimeouts = {};
        let nextCalendarNotifTimeout = null;
        const displayedNotifications = new Set();

        bus_service.addEventListener('notification', ({ detail: notifications }) => {
            for (const { payload, type } of notifications) {
                if (type === "calendar.alarm") {
                    displayCalendarNotification(payload);
                }
            }
        });
        bus_service.start();

        /**
         * Displays the Calendar notification on user's screen
         */
        function displayCalendarNotification(notifications) {
            let lastNotifTimer = 0;

            // Clear previously set timeouts and destroy currently displayed calendar notifications
            browser.clearTimeout(nextCalendarNotifTimeout);
            Object.values(calendarNotifTimeouts).forEach((notif) => browser.clearTimeout(notif));
            calendarNotifTimeouts = {};

            // For each notification, set a timeout to display it
            notifications.forEach(function (notif) {
                const key = notif.event_id + "," + notif.alarm_id;
                if (displayedNotifications.has(key)) {
                    return;
                }
                calendarNotifTimeouts[key] = browser.setTimeout(function () {
                    const notificationRemove = notification.add(notif.message, {
                        title: notif.title,
                        type: "warning",
                        sticky: true,
                        onClose: () => {
                            displayedNotifications.delete(key);
                        },
                        buttons: [
                            {
                                name: env._t("OK"),
                                primary: true,
                                onClick: async () => {
                                    await rpc("/calendar/notify_ack");
                                    notificationRemove();
                                },
                            },
                            {
                                name: env._t("Details"),
                                onClick: async () => {
                                    await action.doAction({
                                        type: 'ir.actions.act_window',
                                        res_model: 'calendar.event',
                                        res_id: notif.event_id,
                                        views: [[false, 'form']],
                                    }
                                    );
                                    notificationRemove();
                                },
                            },
                            {
                                name: env._t("Snooze"),
                                onClick: () => {
                                    notificationRemove();
                                },
                            },
                        ],
                    });
                    displayedNotifications.add(key);
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
                const result = await rpc("/calendar/notify", {}, { silent: true });
                displayCalendarNotification(result);
            } catch (error) {
                if (!(error instanceof ConnectionLostError)) {
                    throw error;
                }
            }
        }
    },
};

registry.category("services").add("calendarNotification", calendarNotificationService);
