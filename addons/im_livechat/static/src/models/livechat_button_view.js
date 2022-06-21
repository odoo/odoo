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
         * @returns {string}
         */
        _computeButtonBackgroundColor() {
            return this.messaging.publicLivechatOptions.button_background_color;
        },
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
         * @returns {string}
         */
         _computeButtonTextColor() {
            return this.messaging.publicLivechatOptions.button_text_color;
        },
        /**
         * @private
         * @returns {integer|FieldCommand}
         */
        _computeChatbotMessageDelay() {
            if (this.isWebsiteLivechatChatbotFlow) {
                return 100;
            }
            return clear();
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeCurrentPartnerId() {
            if (!this.messaging.isPublicLivechatAvailable) {
                return clear();
            }
            return this.messaging.publicLivechatOptions.current_partner_id;
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
         * @returns {string}
         */
        _computeDefaultUsername() {
            if (this.messaging.publicLivechatOptions.default_username) {
                return this.messaging.publicLivechatOptions.default_username;
            }
            return this.env._t("Visitor");
        },
        /**
         * @private
         * @returns {string}
         */
        _computeHeaderBackgroundColor() {
            return this.messaging.publicLivechatOptions.header_background_color;
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
        /**
         * @private
         * @returns {string}
         */
        _computeServerUrl() {
            if (this.isChatbot) {
                return this.messaging.publicLivechatServerUrlChatbot;
            }
            return this.messaging.publicLivechatServerUrl;
        },
        /**
         * @private
         * @returns {string}
         */
        _computeTitleColor() {
            return this.messaging.publicLivechatOptions.title_color;
        },
    },
    fields: {
        autoOpenChatTimeout: attr(),
        buttonBackgroundColor: attr({
            compute: '_computeButtonBackgroundColor',
        }),
        buttonText: attr({
            compute: '_computeButtonText',
        }),
        buttonTextColor: attr({
            compute: '_computeButtonTextColor',
        }),
        chatbot: attr(),
        chatbotCurrentStep: attr(),
        chatbotMessageDelay: attr({
            compute: '_computeChatbotMessageDelay',
            default: 3500, // in milliseconds
        }),
        chatbotState: attr(),
        // livechat window
        chatWindow: attr({
            default: null,
        }),
        currentPartnerId: attr({
            compute: '_computeCurrentPartnerId',
        }),
        defaultMessage: attr({
            compute: '_computeDefaultMessage',
        }),
        defaultUsername: attr({
            compute: '_computeDefaultUsername',
        }),
        headerBackgroundColor: attr({
            compute: '_computeHeaderBackgroundColor',
        }),
        history: attr({
            default: null,
        }),
        inputPlaceholder: attr({
            compute: '_computeInputPlaceholder',
            default: '',
        }),
        isChatbot: attr({
            default: false,
        }),
        isChatbotBatchWelcomeMessages: attr({
            default: false,
        }),
        isChatbotRedirecting: attr({
            default: false,
        }),
        isOpeningChat: attr({
            default: false,
        }),
        isTypingTimeout: attr(),
        isWebsiteLivechatChatbotFlow: attr({
            default: false,
        }),
        // livechat model
        livechat: attr({
            default: null,
        }),
        livechatInit: attr(),
        messages: attr({
            default: [],
        }),
        rule: attr(),
        serverUrl: attr({
            compute: '_computeServerUrl',
        }),
        titleColor: attr({
            compute: '_computeTitleColor',
        }),
    },
});
