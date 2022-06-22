/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Chatbot',
    identifyingFields: ['livechatButtonViewOwner'],
    recordMethods: {
        /**
         * @private
         * @returns {integer|FieldCommand}
         */
        _computeMessageDelay() {
            if (this.livechatButtonViewOwner.isWebsiteLivechatChatbotFlow) {
                return 100;
            }
            return clear();
        },
    },
    fields: {
        data: attr(),
        livechatButtonViewOwner: one('LivechatButtonView', {
            inverse: 'chatbot',
            readonly: true,
            required: true,
        }),
        messageDelay: attr({
            compute: '_computeMessageDelay',
            default: 3500, // in milliseconds
        }),
    },
});
