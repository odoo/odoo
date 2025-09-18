// @ts-check

/** @module @web/views/widgets/notification_alert/notification_alert - Widget displaying a warning banner when browser push notifications are blocked */

import { Component } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

/** Widget that displays a warning banner when browser push notifications are blocked. */
export class NotificationAlert extends Component {
    static props = standardWidgetProps;
    static template = "web.NotificationAlert";

    get isNotificationBlocked() {
        return browser.Notification && browser.Notification.permission === "denied";
    }
}

export const notificationAlert = {
    component: NotificationAlert,
};

registry.category("view_widgets").add("notification_alert", notificationAlert);
