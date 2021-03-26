/** @odoo-module **/

import DiscussSidebar from '@mail/components/discuss_sidebar/discuss_sidebar';

import { patch } from 'web.utils';

const components = { DiscussSidebar };

patch(components.DiscussSidebar.prototype, 'im_livechat/static/src/components/discuss_sidebar/discuss_sidebar.js', {

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
                thread.channel_type === 'livechat' &&
                thread.isPinned &&
                thread.model === 'mail.channel'
            ).sort((c1, c2) => {
                // sort by: last message id (desc), id (desc)
                if (c1.lastMessage && c2.lastMessage) {
                    return c2.lastMessage.id - c1.lastMessage.id;
                }
                // a channel without a last message is assumed to be a new
                // channel just created with the intent of posting a new
                // message on it, in which case it should be moved up.
                if (!c1.lastMessage) {
                    return -1;
                }
                if (!c2.lastMessage) {
                    return 1;
                }
                return c2.id - c1.id;
            });
        if (!this.discuss.sidebarQuickSearchValue) {
            return allOrderedAndPinnedLivechats;
        }
        const qsVal = this.discuss.sidebarQuickSearchValue.toLowerCase();
        return allOrderedAndPinnedLivechats.filter(livechat => {
            const nameVal = livechat.displayName.toLowerCase();
            return nameVal.includes(qsVal);
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _useStoreCompareDepth() {
        return Object.assign(this._super(...arguments), {
            allOrderedAndPinnedLivechats: 1,
        });
    },
    /**
     * Override to include livechat channels on the sidebar.
     *
     * @override
     */
    _useStoreSelector(props) {
        return Object.assign(this._super(...arguments), {
            allOrderedAndPinnedLivechats: this.quickSearchOrderedAndPinnedLivechatList(),
        });
    },

});
