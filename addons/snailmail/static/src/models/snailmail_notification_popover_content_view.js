/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'SnailmailNotificationPopoverContentView',
    fields: {
        iconClass: attr({
            compute() {
                if (!this.notification) {
                    return clear();
                }
                switch (this.notification.notification_status) {
                    case 'sent':
                        return 'fa fa-check';
                    case 'ready':
                        return 'fa fa-clock-o';
                    case 'canceled':
                        return 'fa fa-trash-o';
                    default:
                        return 'fa fa-exclamation text-danger';
                }
            },
            default: '',
        }),
        iconTitle: attr({
            compute() {
                if (!this.notification) {
                    return clear();
                }
                switch (this.notification.notification_status) {
                    case 'sent':
                        return this.env._t("Sent");
                    case 'ready':
                        return this.env._t("Awaiting Dispatch");
                    case 'canceled':
                        return this.env._t("Canceled");
                    default:
                        return this.env._t("Error");
                }
            },
            default: '',
        }),
        message: one('Message', {
            compute() {
                return this.popoverViewOwner.messageViewOwnerAsSnailmailNotificationContent.message;
            },
        }),
        notification: one('Notification', {
            compute() {
                if (!this.message) {
                    return clear();
                }
                // Messages from snailmail are considered to have at most one notification.
                return this.message.notifications[0];
            },
        }),
        popoverViewOwner: one('PopoverView', {
            identifying: true,
            inverse: 'snailmailNotificationPopoverContentView',
        }),
    },
});
