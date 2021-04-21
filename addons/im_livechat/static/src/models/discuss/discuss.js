/** @odoo-module **/

import {
    registerFieldPatchModel,
    registerInstancePatchModel
} from '@mail/model/model_core';
import { attr, one2one, one2many } from '@mail/model/model_field';

registerInstancePatchModel('mail.discuss', 'im_livechat/static/src/models/discuss/discuss.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {String} value
     */
    updateSidebarQuickSearchValue(value) {
        if(!this.sidebarQuickSearchValue) {
            this.categoryLivechat.open();
        }
        this._super(value);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Integer}
     */
    _computeCategoryLivechatUnreadCounter() {
        const counter = this.allPinnedAndSortedLivechatTypeThreads
            .filter(thread => thread.localMessageUnreadCounter > 0).length;
        return counter;
    },

    /**
     * @private
     * @returns [{mail.thread}]
     */
    _computeQuickSearchPinnedAndSortedLivechatTypeThreads() {
        let threads = this.allPinnedAndSortedLivechatTypeThreads;
        if (this.sidebarQuickSearchValue) {
            const qsVal = this.sidebarQuickSearchValue.toLowerCase();
            threads = this.allPinnedAndSortedLivechatTypeThreads.filter(thread => {
                const nameVal = thread.displayName.toLowerCase();
                return nameVal.includes(qsVal);
            })
        }
        return [['replace', threads]];
    }
});

registerFieldPatchModel('mail.discuss', 'im_livechat/static/src/models/discuss/discuss.js', {
    categoryLivechat: one2one('mail.category'),
    categoryLivechatUnreadCounter: attr({
        compute: '_computeCategoryLivechatUnreadCounter',
        dependencies: ['allPinnedAndSortedLivechatTypeThreads', 'allPinnedAndSortedLivechatTypeThreadsLocalMessageUnreadCounter'],
    }),
    allPinnedAndSortedLivechatTypeThreads: one2many('mail.thread', {
        related: 'messaging.allPinnedAndSortedLivechatTypeThreads',
    }),
    allPinnedAndSortedLivechatTypeThreadsLocalMessageUnreadCounter: attr({
        related: 'allPinnedAndSortedLivechatTypeThreads.localMessageUnreadCounter',
    }),
    quickSearchPinnedAndSortedLivechatTypeThreads: one2many('mail.thread', {
        compute: '_computeQuickSearchPinnedAndSortedLivechatTypeThreads',
        dependencies: ['allPinnedAndSortedLivechatTypeThreads', 'sidebarQuickSearchValue'],
    })
});
