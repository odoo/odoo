/** @odoo-module **/

import { registry } from "@web/core/registry";

export const calendarNotificationService = {
    dependencies: ["action", "bus_service", "notification"],

    start(env, { action, bus_service, notification }) {
        bus_service.subscribe("calendar.alarm", displayCalendarNotification);
        bus_service.start();

        /**
         * Displays the Calendar notification on user's screen
         */
        function displayCalendarNotification({ message, title, event_id }) {
            const notificationRemove = notification.add(message, {
                title: title,
                type: "warning",
                sticky: true,
                buttons: [
                    {
                        name: env._t("OK"),
                        primary: true,
                        onClick: async () => {
                            notificationRemove();
                        },
                    },
                    {
                        name: env._t("Details"),
                        onClick: async () => {
                            await action.doAction({
                                type: "ir.actions.act_window",
                                res_model: "calendar.event",
                                res_id: event_id,
                                views: [[false, "form"]],
                            });
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
        }
    },
};

registry.category("services").add("calendarNotification", calendarNotificationService);
