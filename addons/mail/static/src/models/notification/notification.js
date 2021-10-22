/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many2one } from '@mail/model/model_field';
import { clear, insert, insertAndReplace, unlinkAll } from '@mail/model/model_field_command';

registerModel({
    name: 'mail.notification',
    identifyingFields: ['id'],
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
                    data2.partner = unlinkAll();
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
    recordMethods: {
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsFailure() {
            return ['exception', 'bounce'].includes(this.notification_status);
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeIsFromCurrentUser() {
            if (!this.messaging || !this.messaging.currentPartner || !this.message || !this.message.author) {
                return clear();
            }
            return this.messaging.currentPartner === this.message.author;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeNotificationGroup() {
            if (!this.isFailure || !this.isFromCurrentUser) {
                return clear();
            }
            const thread = this.message.originThread;
            // Notifications are grouped by model and notification_type.
            // Except for channel where they are also grouped by id because
            // we want to open the actual channel in discuss or chat window
            // and not its kanban/list/form view.
            return insertAndReplace({
                notification_type: this.notification_type,
                res_id: thread.model === 'mail.channel' ? thread.id : null,
                res_model: thread.model,
                res_model_name: thread.model_name,
            });
        },
    },
    fields: {
        failure_type: attr(),
        id: attr({
            readonly: true,
            required: true,
        }),
        isFailure: attr({
            compute: '_computeIsFailure',
        }),
        isFromCurrentUser: attr({
            compute: '_computeIsFromCurrentUser',
        }),
        message: many2one('mail.message', {
            inverse: 'notifications',
        }),
        notificationGroup: many2one('mail.notification_group', {
            compute: '_computeNotificationGroup',
            inverse: 'notifications',
        }),
        notification_status: attr(),
        notification_type: attr(),
        partner: many2one('mail.partner'),
    },
});
