import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { Component } from "@odoo/owl";

export class NotificationAlertDialog extends Component {
    static components = { Dialog };
    static props = ["close"];
    static template = "web.NotificationAlertDialog";
}

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
