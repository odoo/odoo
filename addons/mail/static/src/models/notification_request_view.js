/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'NotificationRequestView',
    identifyingFields: ['notificationListViewOwner'],
    recordMethods: {
        /**
         * Handle the response of the user when prompted whether push notifications
         * are granted or denied.
         *
         * @param {string} value
         */
        handleResponseNotificationPermission(value) {
            this.messaging.refreshIsNotificationPermissionDefault();
            if (value !== 'granted') {
                this.env.services['bus_service'].sendNotification({
                    message: this.env._t("Odoo will not have the permission to send native notifications on this device."),
                    title: this.env._t("Permission denied"),
                });
            }
        },
    },
    fields: {
        notificationListViewOwner: one('NotificationListView', {
            inverse: 'notificationRequestView',
            required: true,
            readonly: true,
        }),
    },
});
