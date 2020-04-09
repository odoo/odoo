odoo.define('im_livechat.messaging.component.DiscussSidebar', function (require) {
'use strict';

const components = {
    DiscussSidebar: require('mail.messaging.component.DiscussSidebar'),
};

const { patch } = require('web.utils');

patch(components.DiscussSidebar, 'im_livechat.messaging.component.DiscussSidebar', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Return the list of livechats that match the quick search value input.
     *
     * @returns {mail.messaging.entity.Thread[]}
     */
    quickSearchOrderedAndPinnedLivechatList() {
        const allOrderedAndPinnedLivechats = this.env.entities.Thread.allOrderedAndPinnedLivechats();
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
            allOrderedAndPinnedLivechats: this.env.entities.Thread.allOrderedAndPinnedLivechats(),
        });
    },

});

});
