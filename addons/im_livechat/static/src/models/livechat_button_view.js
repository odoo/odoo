/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerModel({
    name: 'LivechatButtonView',
    identifyingFields: ['messaging'],
    recordMethods: {
        /**
         * @private
         * @returns {string}
         */
        _computeButtonText() {
            if (this.messaging.publicLivechatOptions.button_text) {
                return this.messaging.publicLivechatOptions.button_text;
            }
            return this.env._t("Chat with one of our collaborators");
        },
    },
    fields: {
        buttonText: attr({
            compute: '_computeButtonText',
        }),
    },
});
