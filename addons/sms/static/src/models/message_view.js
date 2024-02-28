/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'MessageView',
    fields: {
        failureNotificationIconClassName: {
            compute() {
                if (this.message && this.message.message_type === 'sms') {
                    return 'fa fa-mobile';
                }
                return this._super();
            },
        },
        failureNotificationIconLabel: {
            compute() {
                if (this.message && this.message.message_type === 'sms') {
                    return this.env._t("SMS");
                }
                return this._super();
            },
        },
        notificationIconClassName: {
            compute() {
                if (this.message && this.message.message_type === 'sms') {
                    return 'fa fa-mobile';
                }
                return this._super();
            },
        },
        notificationIconLabel: {
            compute() {
                if (this.message && this.message.message_type === 'sms') {
                    return this.env._t("SMS");
                }
                return this._super();
            },
        },
    },
});
