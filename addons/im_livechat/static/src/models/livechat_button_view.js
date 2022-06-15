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
        _computeDefaultMessage() {
            if (this.messaging.publicLivechatOptions.default_message) {
                return this.messaging.publicLivechatOptions.default_message;
            }
            return this.env._t("How may I help you?");
        },
    },
    fields: {
        defaultMessage: attr({
            compute: '_computeDefaultMessage',
        }),
    },
});
