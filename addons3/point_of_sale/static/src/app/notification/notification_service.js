/** @odoo-module */

import { reactive, Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Transition } from "@web/core/transition";

const TRANSITION_LEAVE_DURATION = 200; // ms

class Notification extends Component {
    static template = "point_of_sale.Notification";
    static props = { message: String, close: Function, className: String };
}

class NotificationContainer extends Component {
    static template = "point_of_sale.NotificationContainer";
    static components = { Transition, Notification };
    static props = {
        notifications: Object,
    };
    leaveDuration = TRANSITION_LEAVE_DURATION;
}
// FIXME: probably should use the main notification service from web long term.
export const notificationService = {
    start() {
        const notifications = reactive({});
        let notifId = 0;
        registry.category("main_components").add("PosNotificationContainer", {
            Component: NotificationContainer,
            props: { notifications },
        });
        return {
            add(message, duration = 2000) {
                const id = ++notifId;
                notifications[id] = {
                    message,
                    visible: true,
                    close() {
                        notifications[id].visible = false;
                    },
                    delete() {
                        delete notifications[id];
                    },
                };
                setTimeout(() => notifications?.[id]?.close(), duration);
            },
        };
    },
};

registry.category("services").add("pos_notification", notificationService);
