/** @odoo-module **/

import { addFields, patchIdentifyingFields, patchRecordMethods } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';
import '@mail/models/notification_list_view/notification_list_view'; // ensure the model definition is loaded before the patch

addFields('mail.notification_list_view', {
    qunitTestOwner: one2one('mail.qunit_test', {
        inverse: 'notificationListView',
        readonly: true,
    }),
});

patchIdentifyingFields('mail.notification_list_view', identifyingFields => {
    identifyingFields[0].push('qunitTestOwner');
});

patchRecordMethods('mail.notification_list_view', {
    _computeFilter() {
        if (this.qunitTestOwner) {
            return this.filter;
        }
        return this._super();
    },
});
