/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'Chatbot',
    identifyingFields: ['livechatButtonViewOwner'],
    recordMethods: {
        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            return this.data.name;
        },
    },
    fields: {
        data: attr(),
        livechatButtonViewOwner: one('LivechatButtonView', {
            inverse: 'chatbot',
            readonly: true,
            required: true,
        }),
        name: attr({
            compute: '_computeName',
        }),
    },
});
