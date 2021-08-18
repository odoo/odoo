/** @odoo-module **/

import { NotificationList } from '@mail/components/notification_list/notification_list';
import { patch } from 'web.utils';

const components = { NotificationList };

components.NotificationList._allowedFilters.push('livechat');

patch(components.NotificationList.prototype, 'im_livechat/static/src/components/notification_list/notification_list.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Override to include livechat channels.
     *
     * @override
     */
    _getThreads(props) {
        if (props.filter === 'livechat') {
            return this.messaging.models['mail.thread'].all(thread =>
                thread.channel_type === 'livechat' &&
                thread.isPinned &&
                thread.model === 'mail.channel'
            );
        }
        return this._super(...arguments);
    },

});
