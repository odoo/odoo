odoo.define('im_livechat.messaging.component.NotificationList', function (require) {
'use strict';

const components = {
    NotificationList: require('mail.messaging.component.NotificationList'),
};

const { patch } = require('web.utils');

components.NotificationList._allowedFilters.push('livechat');

patch(components.NotificationList, 'im_livechat.messaging.component.NotificationList', {

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
            return this.env.entities.Thread.allOrderedAndPinnedLivechats();
        }
        return this._super(...arguments);
    },

});

});
