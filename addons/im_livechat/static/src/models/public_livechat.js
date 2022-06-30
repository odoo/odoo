/** @odoo-module **/

import PublicLivechat from '@im_livechat/legacy/models/public_livechat';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechat',
    identifyingFields: ['livechatButtonOwner'],
    lifecycleHooks: {
        _created() {
            this.update({
                legacyPublicLivechat: new PublicLivechat({
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
    },
});
