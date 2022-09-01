/** @odoo-module **/

import { addFields, addRecordMethods, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/thread';

addFields('Thread', {
    /**
     * If set, current thread is a livechat.
     */
    messagingAsPinnedLivechat: one('Messaging', {
        compute: '_computeMessagingAsPinnedLivechat',
        inverse: 'pinnedLivechats',
    }),
});

addRecordMethods('Thread', {
    /**
     * @private
     * @returns {FieldCommand}
     */
    _computeMessagingAsPinnedLivechat() {
        if (!this.messaging || !this.channel || this.channel.channel_type !== 'livechat' || !this.isPinned) {
            return clear();
        }
        return this.messaging;
    },
});

patchRecordMethods('Thread', {
    /**
     * @override
     */
    getMemberName(persona) {
        if (this.channel && this.channel.channel_type === 'livechat' && persona.partner && persona.partner.user_livechat_username) {
            return persona.partner.user_livechat_username;
        }
        if (this.channel && this.channel.channel_type === 'livechat' && persona.partner && persona.partner.is_public && this.channel.anonymous_name) {
            return this.channel.anonymous_name;
        }
        return this._super(persona);
    },
    /**
     * @override
     */
    _computeHasInviteFeature() {
        if (this.channel && this.channel.channel_type === 'livechat') {
            return true;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeHasMemberListFeature() {
        if (this.channel && this.channel.channel_type === 'livechat') {
            return true;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeIsChatChannel() {
        if (this.channel && this.channel.channel_type === 'livechat') {
            return true;
        }
        return this._super();
    },
});
