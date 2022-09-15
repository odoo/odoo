/** @odoo-module **/

import { patchFields } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/notification_group_view';

patchFields('NotificationGroupView', {
    imageSrc: {
        compute() {
            if (this.notificationGroup.notification_type === 'sms') {
                return '/sms/static/img/sms_failure.svg';
            }
            return this._super();
        },
    },
});
