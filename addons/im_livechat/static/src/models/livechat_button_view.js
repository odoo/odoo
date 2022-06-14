/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'LivechatButtonView',
    identifyingFields: ['messaging'],
    recordMethods: {
        /**
         * @returns {string}
         */
        _computeButtonText() {
            if (this.messaging.publicLivechatOptions.button_text) {
                return this.messaging.publicLivechatOptions.button_text;
            }
            return this.env._t("Chat with one of our collaborators");
        },
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
        autoOpenChatTimeout: attr(),
        buttonText: attr({
            compute: '_computeButtonText',
        }),
        // livechat window
        chatWindow: attr({
            default: null,
        }),
        defaultMessage: attr({
            compute: '_computeDefaultMessage',
        }),
        inputPlaceholder: attr({
            compute: '_computeInputPlaceholder',
            default: '',
        }),
        isChatbot: attr({
            default: false,
        }),
        isOpeningChat: attr({
            default: false,
        }),
    },
});
