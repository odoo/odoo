odoo.define('im_livechat.messaging.component.DiscussSidebarItem', function (require) {
'use strict';

const components = {
    DiscussSidebarItem: require('mail.messaging.component.DiscussSidebarItem'),
};

const { patch } = require('web.utils');

patch(components.DiscussSidebarItem, 'im_livechat.messaging.component.DiscussSidebarItem', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    hasUnpin(...args) {
        const res = this._super(...args);
        return res || this.thread.channel_type === 'livechat';
    }

});

});
