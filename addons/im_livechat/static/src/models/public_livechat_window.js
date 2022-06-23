/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'PublicLivechatWindow',
    identifyingFields: ['livechatButtonViewOwner'],
    lifecycleHooks: {
        _willDelete() {
            this.legacyChatWindow.destroy();
        },
    },
    fields: {
        legacyChatWindow: attr({
            default: null,
        }),
        livechatButtonViewOwner: one('LivechatButtonView', {
            inverse: 'chatWindow',
            readonly: true,
            required: true,
        }),
    },
});
