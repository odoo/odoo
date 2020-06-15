odoo.define('im_livechat/static/src/components/notification_list/notification_list.js', function (require) {
'use strict';

const components = {
    NotificationList: require('mail/static/src/components/notification_list/notification_list.js'),
};

const { patch } = require('web.utils');

components.NotificationList._allowedFilters.push('livechat');

patch(components.NotificationList, 'im_livechat/static/src/components/notification_list/notification_list.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Override to include livechat channels.
     *
     * @override
     */
    _useStoreSelectorThreads(props) {
        if (props.filter === 'livechat') {
            return this.env.models['mail.thread'].all(thread =>
                thread.channel_type === 'livechat' &&
                thread.isPinned &&
                thread.model === 'mail.channel'
            );
        }
        return this._super(...arguments);
    },

});

});
