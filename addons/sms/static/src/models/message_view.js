/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/message_view';

patchRecordMethods('MessageView', {
    /**
     * @override
     */
    _computeFailureNotificationIconClassName() {
        if (this.message && this.message.message_type === 'sms') {
            return 'fa fa-mobile';
        }
        return this._super();
    },
    /**
     * @override
     */
     _computeFailureNotificationIconLabel() {
        if (this.message && this.message.message_type === 'sms') {
            return this.env._t("SMS");
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeNotificationIconClassName() {
        if (this.message && this.message.message_type === 'sms') {
            return 'fa fa-mobile';
        }
        return this._super();
    },
    /**
     * @override
     */
     _computeNotificationIconLabel() {
        if (this.message && this.message.message_type === 'sms') {
            return this.env._t("SMS");
        }
        return this._super();
    },
});
