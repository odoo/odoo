odoo.define('im_livechat/static/src/components/discuss_sidebar/discuss_sidebar.js', function (require) {
'use strict';

const components = {
    DiscussSidebar: require('mail/static/src/components/discuss_sidebar/discuss_sidebar.js'),
};

const { patch } = require('web.utils');

patch(components.DiscussSidebar, 'im_livechat/static/src/components/discuss_sidebar/discuss_sidebar.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Return the list of livechats that match the quick search value input.
     *
     * @returns {mail.thread[]}
     */
    quickSearchOrderedAndPinnedLivechatList() {
        const allOrderedAndPinnedLivechats = this.env.models['mail.thread']
            .all(thread =>
                thread.__mfield_channel_type(this) === 'livechat' &&
                thread.__mfield_isPinned(this) &&
                thread.__mfield_model(this) === 'mail.channel'
            ).sort((c1, c2) => {
                // sort by: last message id (desc), id (desc)
                if (c1.__mfield_lastMessage(this) && c2.__mfield_lastMessage(this)) {
                    return c2.__mfield_lastMessage(this).__mfield_id(this) - c1.__mfield_lastMessage(this).__mfield_id(this);
                }
                // a channel without a last message is assumed to be a new
                // channel just created with the intent of posting a new
                // message on it, in which case it should be moved up.
                if (!c1.__mfield_lastMessage(this)) {
                    return -1;
                }
                if (!c2.__mfield_lastMessage(this)) {
                    return 1;
                }
                return c2.__mfield_id(this) - c1.__mfield_id(this);
            });
        if (!this.discuss.__mfield_sidebarQuickSearchValue(this)) {
            return allOrderedAndPinnedLivechats;
        }
        const qsVal = this.discuss.__mfield_sidebarQuickSearchValue(this).toLowerCase();
        return allOrderedAndPinnedLivechats.filter(livechat => {
            const nameVal = livechat.__mfield_displayName(this).toLowerCase();
            return nameVal.includes(qsVal);
        });
    },

});

});
