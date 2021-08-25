/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';

registerInstancePatchModel('mail.discuss_sidebar_category_item', 'im_livechat/static/src/models/discuss_sidebar_category_item/discuss_sidebar_category_item.js', {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

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
