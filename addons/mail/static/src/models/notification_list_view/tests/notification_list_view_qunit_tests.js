/** @odoo-module **/

import { addFields, patchIdentifyingFields, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import '@mail/models/notification_list_view/notification_list_view'; // ensure the model definition is loaded before the patch

addFields('NotificationListView', {
    qunitTestOwner: one('QUnitTest', {
        inverse: 'notificationListView',
        readonly: true,
    }),
});

patchIdentifyingFields('NotificationListView', identifyingFields => {
    identifyingFields[0].push('qunitTestOwner');
});

patchRecordMethods('NotificationListView', {
    _computeFilter() {
        if (this.qunitTestOwner) {
            return this.filter;
        }
        return this._super();
    },
});
