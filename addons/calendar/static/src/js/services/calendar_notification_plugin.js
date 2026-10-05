import { BusPlugin } from "@bus/services/bus_plugin";
import { markup, onWillDestroy, Plugin, usePlugin, useScope } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError, rpc } from "@web/core/network/rpc";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { services } from "@web/core/services";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

export class CalendarNotificationPlugin extends Plugin {
    action = usePlugin(ActionPlugin);
    bus = usePlugin(BusPlugin);
    notification = usePlugin(NotificationPlugin);

    /** @type {number[]} */
    calendarNotifTimeouts = [];
    displayedNotifications = new Set();

    setup() {
        /**
         * @param {any[]} notifications
         */
        const displayCalendarNotification = (notifications) => {
            let lastNotifTimer = 0;

            // Clear previously set timeouts and destroy currently displayed calendar notifications
            this._clearTimeouts();

            // For each notification, set a timeout to display it
            for (const notif of notifications) {
                const key = [notif.event_id, notif.alarm_id].join(",");
                if (this.displayedNotifications.has(key)) {
                    continue;
                }
                const timeout = setTimeout(() => {
                    const notificationRemove = this.notification.add(markup(notif.message), {
                        title: notif.title,
                        type: "warning",
                        sticky: true,
                        onClose: () => {
                            this.displayedNotifications.delete(key);
                        },
                        buttons: [
                            {
                                name: _t("OK"),
                                onClick: async () => {
                                    await rpc("/calendar/notify_ack");
                                    notificationRemove();
                                },
                            },
                            {
                                name: _t("Details"),
                                onClick: async () => {
                                    await this.action.doAction({
                                        type: "ir.actions.act_window",
                                        res_model: "calendar.event",
                                        res_id: notif.event_id,
                                        views: [[false, "form"]],
                                    });
                                    notificationRemove();
                                },
                            },
                        ],
                        className: "o_line_clamp_5",
                    });
                    this.displayedNotifications.add(key);
                }, notif.timer * 1000);
                this.calendarNotifTimeouts.push(timeout);
                lastNotifTimer = Math.max(lastNotifTimer, notif.timer);
            }

            // Set a timeout to get the next notifications when the last one has been displayed
            if (lastNotifTimer > 0) {
                this.calendarNotifTimeouts.push(
                    setTimeout(getNextCalendarNotif, lastNotifTimer * 1000)
                );
            }
        };

        async function getNextCalendarNotif() {
            try {
                const result = await rpc("/calendar/notify", {}, { silent: true });
                if (!scope.isDestroyed()) {
                    displayCalendarNotification(result);
                }
            } catch (error) {
                if (!(error instanceof ConnectionLostError)) {
                    throw error;
                }
            }
        }

        const scope = useScope();
        const unsubscribe = this.bus.subscribe("calendar.alarm", displayCalendarNotification);
        this.bus.start();

        onWillDestroy(() => {
            unsubscribe();
            this._clearTimeouts();
        });
    }

    /** @private */
    _clearTimeouts() {
        for (const timeout of this.calendarNotifTimeouts) {
            clearTimeout(timeout);
        }
        this.calendarNotifTimeouts.length = 0;
    }
}

services.add(CalendarNotificationPlugin);
