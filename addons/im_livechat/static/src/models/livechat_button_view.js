/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'LivechatButtonView',
    identifyingFields: ['messaging'],
    recordMethods: {
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeInputPlaceholder() {
            if (this.isChatbot) {
                // void the default livechat placeholder in the user input
                // as we use it for specific things (e.g: showing "please select an option above")
                return clear();
            }
            if (this.messaging.publicLivechatOptions.input_placeholder) {
                return this.messaging.publicLivechatOptions.input_placeholder;
            }
            return this.env._t("Ask something ...");
        },
    },
    fields: {
        inputPlaceholder: attr({
            compute: '_computeInputPlaceholder',
            default: '',
        }),
        isChatbot: attr({
            default: false,
        }),
    },
});
