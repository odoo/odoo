/** @odoo-module **/

import PublicLivechat from '@im_livechat/legacy/models/public_livechat';

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'PublicLivechat',
    identifyingFields: ['livechatButtonOwner'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand|im_livechat/legacy/models/public_livechat}
         */
        _computeLegacyPublicLivechat() {
            if (!this.data) {
                return clear();
            }
            return new PublicLivechat({
                parent: this.livechatButtonOwner.widget,
                data: this.data,
            });
        },
    },
    fields: {
        data: attr(),
        legacyPublicLivechat: attr({
            compute: '_computeLegacyPublicLivechat',
        }),
        livechatButtonOwner: one('LivechatButtonView', {
            inverse: 'publicLivechat',
            readonly: true,
            required: true,
        }),
    },
});
