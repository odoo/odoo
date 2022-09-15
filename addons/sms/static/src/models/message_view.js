/** @odoo-module **/

import { patchFields } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/message_view';

patchFields('MessageView', {
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
});
