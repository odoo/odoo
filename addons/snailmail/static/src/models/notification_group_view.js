/** @odoo-module **/

import { patchFields } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/notification_group_view';

patchFields('NotificationGroupView', {
    imageSrc: {
        compute() {
            if (this.notificationGroup.notification_type === 'snail') {
                return '/snailmail/static/img/snailmail_failure.png';
            }
            return this._super();
        },
    },
});
