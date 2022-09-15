/** @odoo-module **/

import { addFields, patchFields, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/thread';

addFields('Thread', {
    /**
     * If set, current thread is a livechat.
     */
    messagingAsPinnedLivechat: one('Messaging', {
        compute() {
            if (!this.messaging || !this.channel || this.channel.channel_type !== 'livechat' || !this.isPinned) {
                return clear();
            }
            return this.messaging;
        },
        inverse: 'pinnedLivechats',
    }),
});

patchFields('Thread', {
    hasInviteFeature: {
        compute() {
            if (this.channel && this.channel.channel_type === 'livechat') {
                return true;
            }
            return this._super();
        },
    },
    hasMemberListFeature: {
        compute() {
            if (this.channel && this.channel.channel_type === 'livechat') {
                return true;
            }
            return this._super();
        },
    },
    isChatChannel: {
        compute() {
            if (this.channel && this.channel.channel_type === 'livechat') {
                return true;
            }
            return this._super();
        },
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
});
