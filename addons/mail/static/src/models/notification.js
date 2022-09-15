/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insert } from '@mail/model/model_field_command';

registerModel({
    name: 'Notification',
    modelMethods: {
        /**
         * @param {Object} data
         * @return {Object}
         */
        convertData(data) {
            const data2 = {};
            if ('failure_type' in data) {
                data2.failure_type = data.failure_type;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('notification_status' in data) {
                data2.notification_status = data.notification_status;
            }
            if ('notification_type' in data) {
                data2.notification_type = data.notification_type;
            }
            if ('res_partner_id' in data) {
                if (!data.res_partner_id) {
                    data2.partner = clear();
                } else {
                    data2.partner = insert({
                        display_name: data.res_partner_id[1],
                        id: data.res_partner_id[0],
                    });
                }
            }
            return data2;
        },
    },
    fields: {
        failure_type: attr(),
        /**
         * Determines the classname of the icon for this notification.
         */
        iconClass: attr({
            compute() {
                switch (this.notification_status) {
                    case 'sent':
                        return 'fa fa-check';
                    case 'bounce':
                        return 'fa fa-exclamation';
                    case 'exception':
                        return 'fa fa-exclamation';
                    case 'ready':
                        return 'fa fa-send-o';
                    case 'canceled':
                        return 'fa fa-trash-o';
                }
                return '';
            },
        }),
        /**
         * Determines the text to display as title for this notification.
         */
        iconTitle: attr({
            compute() {
                switch (this.notification_status) {
                    case 'sent':
                        return this.env._t("Sent");
                    case 'bounce':
                        return this.env._t("Bounced");
                    case 'exception':
                        return this.env._t("Error");
                    case 'ready':
                        return this.env._t("Ready");
                    case 'canceled':
                        return this.env._t("Canceled");
                }
                return '';
            },
        }),
        id: attr({
            identifying: true,
        }),
        isFailure: attr({
            compute() {
                return ['exception', 'bounce'].includes(this.notification_status);
            },
        }),
        isFromCurrentUser: attr({
            compute() {
                if (!this.messaging || !this.messaging.currentPartner || !this.message || !this.message.author) {
                    return clear();
                }
                return this.messaging.currentPartner === this.message.author;
            },
        }),
        message: one('Message', {
            inverse: 'notifications',
        }),
        notificationGroup: one('NotificationGroup', {
            compute() {
                if (!this.isFailure || !this.isFromCurrentUser) {
                    return clear();
                }
                const thread = this.message.originThread;
                // Notifications are grouped by model and notification_type.
                // Except for channel where they are also grouped by id because
                // we want to open the actual channel in discuss or chat window
                // and not its kanban/list/form view.
                return {
                    notification_type: this.notification_type,
                    res_id: thread.model === 'mail.channel' ? thread.id : null,
                    res_model: thread.model,
                    res_model_name: thread.model_name,
                };
            },
            inverse: 'notifications',
        }),
        notification_status: attr(),
        notification_type: attr(),
        partner: one('Partner'),
    },
});
