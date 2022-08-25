/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/discuss_sidebar_category_item';

patchRecordMethods('DiscussSidebarCategoryItem', {
    /**
     * @override
     */
    _computeAvatarUrl() {
        if (this.channel && this.channel.channel_type === 'livechat') {
            if (this.thread.correspondent && this.thread.correspondent.id > 0) {
                return this.thread.correspondent.avatarUrl;
            }
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeCategoryCounterContribution() {
        if (this.channel && this.channel.channel_type === 'livechat') {
            return this.thread.localMessageUnreadCounter > 0 ? 1 : 0;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeCounter() {
        if (this.channel && this.channel.channel_type === 'livechat') {
            return this.thread.localMessageUnreadCounter;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeHasUnpinCommand() {
        if (this.channel && this.channel.channel_type === 'livechat') {
            return !this.thread.localMessageUnreadCounter;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeHasThreadIcon() {
        if (this.channel && this.channel.channel_type === 'livechat') {
            return clear();
        }
        return this._super();
    },
});
