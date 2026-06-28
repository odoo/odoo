import { Component } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { NotificationAlertDialog } from "@web/core/notification_alert_dialog/notification_alert_dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class NotificationAlert extends Component {
    static props = standardWidgetProps;
    static template = "web.NotificationAlert";

    setup() {
        this.dialog = useService("dialog");
    }

    get isNotificationBlocked() {
        return browser.Notification && browser.Notification.permission === "denied";
    }

    openNotificationDialog() {
        this.dialog.add(NotificationAlertDialog);
    }
}

export const notificationAlert = {
    component: NotificationAlert,
};

registry.category("view_widgets").add("notification_alert", notificationAlert);
