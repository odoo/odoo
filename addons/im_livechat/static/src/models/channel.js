/** @odoo-module **/

import { addFields, addRecordMethods, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/channel';

addFields('Channel', {
    /**
     * If set, current thread is a livechat.
     */
    messagingAsPinnedLivechat: one('Messaging', {
        compute: '_computeMessagingAsPinnedLivechat',
        inverse: 'pinnedLivechats',
    }),
});

addRecordMethods('Channel', {
    /**
     * @private
     * @returns {FieldCommand}
     */
    _computeMessagingAsPinnedLivechat() {
        if (this.channel_type !== 'livechat' || !this.isPinned) {
            return clear();
        }
        return replace(this.messaging);
    },
});

patchRecordMethods('Channel', {
    /**
     * @override
     */
    _computeCorrespondent() {
        if (this.channel_type === 'livechat') {
            // livechat correspondent never changes: always the public member.
            return;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeHasMemberListFeature() {
        return this.channel_type === 'livechat' || this._super();
    },
    /**
     * @override
     */
    _computeHasSeenIndicators() {
        return this.channel_type === 'livechat' || this._super();
    },
    /**
     * @override
     */
    _computeIsChat() {
        return this.channel_type === 'livechat' || this._super();
    },
    /**
     * @override
     */
    _getDiscussSidebarCategory() {
        if (this.channel_type === 'livechat') {
            return this.messaging.discuss.categoryLivechat;
        }
        return this._super();
    }
});
