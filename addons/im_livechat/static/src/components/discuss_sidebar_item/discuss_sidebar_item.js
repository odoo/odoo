odoo.define('im_livechat/static/src/components/discuss_sidebar_item/discuss_sidebar_item.js', function (require) {
'use strict';

const components = {
    DiscussSidebarItem: require('mail/static/src/components/discuss_sidebar_item/discuss_sidebar_item.js'),
};

const { patch } = require('web.utils');

patch(components.DiscussSidebarItem, 'im_livechat/static/src/components/discuss_sidebar_item/discuss_sidebar_item.js', {

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
