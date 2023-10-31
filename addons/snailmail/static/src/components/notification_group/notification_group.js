/** @odoo-module **/

import { NotificationGroup } from '@mail/components/notification_group/notification_group';

import { patch } from 'web.utils';

patch(NotificationGroup.prototype, 'snailmail/static/src/components/notification_group/notification_group.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    image() {
        if (this.group.notification_type === 'snail') {
            return '/snailmail/static/img/snailmail_failure.png';
        }
        return this._super(...arguments);
    },
});
