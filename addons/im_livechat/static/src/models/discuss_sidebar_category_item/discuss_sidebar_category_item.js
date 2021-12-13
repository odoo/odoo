/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/discuss_sidebar_category_item/discuss_sidebar_category_item';

patchRecordMethods('DiscussSidebarCategoryItem', {
    /**
     * @override
     */
    _computeAvatarUrl() {
        if (this.channelType === 'livechat') {
            if (this.channel.correspondent && this.channel.correspondent.id > 0) {
                return this.channel.correspondent.avatarUrl;
            }
            return '/mail/static/src/img/smiley/avatar.jpg';
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeCategoryCounterContribution() {
        switch (this.channel.channel_type) {
            case 'livechat':
                return this.channel.localMessageUnreadCounter > 0 ? 1 : 0;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeCounter() {
        if (this.channelType === 'livechat') {
            return this.channel.localMessageUnreadCounter;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeHasUnpinCommand() {
        if (this.channelType === 'livechat') {
            return !this.channel.localMessageUnreadCounter;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeHasThreadIcon() {
        if (this.channelType === 'livechat') {
            return false;
        }
        return this._super();
    },
});
