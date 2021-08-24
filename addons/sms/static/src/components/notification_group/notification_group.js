/** @odoo-module **/

import { NotificationGroup } from '@mail/components/notification_group/notification_group';

import { patch } from 'web.utils';

patch(NotificationGroup.prototype, 'sms/static/src/components/notification_group/notification_group.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    image() {
        if (this.group.notification_type === 'sms') {
            return '/sms/static/img/sms_failure.svg';
        }
        return this._super(...arguments);
    },
});
