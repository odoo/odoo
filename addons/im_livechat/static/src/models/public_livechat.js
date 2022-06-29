/** @odoo-module **/

import PublicLivechat from '@im_livechat/legacy/models/public_livechat';

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechat',
    identifyingFields: ['livechatButtonOwner'],
    lifecycleHooks: {
        _created() {
            this.update({
                legacyPublicLivechat: new PublicLivechat(this.messaging, {
                    parent: this.livechatButtonOwner.widget,
                    data: this.data,
                }),
            });
        },
        _willDelete() {
            this.legacyPublicLivechat.destroy();
        },
    },
    recordMethods: {
    },
    fields: {
        data: attr(),
        legacyPublicLivechat: attr(),
        livechatButtonOwner: one('LivechatButtonView', {
            inverse: 'publicLivechat',
            readonly: true,
            required: true,
        }),
        messages: many('PublicLivechatMessage'),
        // amount of messages that have not yet been read on this chat
        unreadCounter: attr({
            default: 0,
        }),
    },
});
