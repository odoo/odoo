/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'SnailmailNotificationPopoverContentView',
    recordMethods: {
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeIconClass() {
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
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeIconTitle() {
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
        /**
         * @private
         * @returns {Message}
         */
        _computeMessage() {
            return this.popoverViewOwner.messageViewOwnerAsSnailmailNotificationContent.message;
        },
        /**
         * @private
         * @returns {Notification|FieldCommand}
         */
        _computeNotification() {
            if (!this.message) {
                return clear();
            }
            // Messages from snailmail are considered to have at most one notification.
            return this.message.notifications[0];
        },
    },
    fields: {
        iconClass: attr({
            compute: '_computeIconClass',
            default: '',
        }),
        iconTitle: attr({
            compute: '_computeIconTitle',
            default: '',
        }),
        message: one('Message', {
            compute: '_computeMessage',
        }),
        notification: one('Notification', {
            compute: '_computeNotification',
        }),
        popoverViewOwner: one('PopoverView', {
            identifying: true,
            inverse: 'snailmailNotificationPopoverContentView',
        }),
    },
});
