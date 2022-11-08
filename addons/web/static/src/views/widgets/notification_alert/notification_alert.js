/** @odoo-module **/

import { browser } from '@web/core/browser/browser';
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { Component } from '@odoo/owl';

export class NotificationAlert extends Component {
    get isNotificationBlocked() {
        return browser.Notification && browser.Notification.permission === 'denied';
    }
}

Object.assign(NotificationAlert, {
    props: standardWidgetProps,
    template: 'web.NotificationAlert',
});

registry.category("view_widgets").add("notification_alert", NotificationAlert);
