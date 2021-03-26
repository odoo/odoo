/** @odoo-module **/

import DiscussSidebarItem from '@mail/components/discuss_sidebar_item/discuss_sidebar_item';

import { patch } from 'web.utils';

const components = { DiscussSidebarItem };

patch(components.DiscussSidebarItem.prototype, 'im_livechat/static/src/components/discuss_sidebar_item/discuss_sidebar_item.js', {

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
