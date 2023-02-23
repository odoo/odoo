/** @odoo-module **/

import { Patch } from '@mail/model';

Patch({
    name: 'NotificationGroupView',
    fields: {
        imageSrc: {
            compute() {
                if (this.notificationGroup.notification_type === 'sms') {
                    return '/sms/static/img/sms_failure.svg';
                }
                return this._super();
            },
        },
    },
});
