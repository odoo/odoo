/** @odoo-module **/

import PublicLivechatMessage from '@im_livechat/legacy/models/public_livechat_message';

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'LivechatButtonView',
    identifyingFields: ['publicLivechatGlobalOwner'],
    recordMethods: {
        /**
         * @param {Object} data
         * @param {Object} [options={}]
         */
        addMessage(data, options) {
            const legacyMessage = new PublicLivechatMessage(this, this.messaging, data);

            const hasAlreadyMessage = _.some(this.messages, function (msg) {
                return legacyMessage.getID() === msg.id;
            });
            if (hasAlreadyMessage) {
                return;
            }
            const message = this.messaging.models['PublicLivechatMessage'].insert({
                data,
                id: data.id,
                legacyPublicLivechatMessage: legacyMessage,
            });

            if (this.messaging.publicLivechatGlobal.publicLivechat && this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat) {
                this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat.addMessage(legacyMessage);
            }

            if (options && options.prepend) {
                this.update({
                    messages: replace([message, ...this.messages]),
                });
            } else {
                this.update({
                    messages: replace([...this.messages, message]),
                });
            }
        },
        /**
         * See '_chatbotSaveSession'.
         *
         * We retrieve the livechat uuid from the session cookie since the livechat Widget is not yet
         * initialized when we restore the chatbot state.
         *
         * We also clear any older keys that store a previously saved chatbot session.
         * (In that case we clear the actual browser's local storage, we don't use the localStorage
         * object as it does not allow browsing existing keys, see 'local_storage.js'.)
         */
        chatbotRestoreSession() {
            const browserLocalStorage = window.localStorage;
            if (browserLocalStorage && browserLocalStorage.length) {
                for (let i = 0; i < browserLocalStorage.length; i++) {
                    const key = browserLocalStorage.key(i);
                    if (key.startsWith('im_livechat.chatbot.state.uuid_') && key !== this.chatbotSessionCookieKey) {
                        browserLocalStorage.removeItem(key);
                    }
                }
            }
            const chatbotState = localStorage.getItem(this.chatbotSessionCookieKey);
            if (chatbotState) {
                this.chatbot.update({ currentStep: insertAndReplace({ data: this.localStorageChatbotState._chatbotCurrentStep }) });
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeButtonBackgroundColor() {
            return this.messaging.publicLivechatGlobal.options.button_background_color;
        },
        /**
         * @returns {string}
         */
        _computeButtonText() {
            if (this.messaging.publicLivechatGlobal.options.button_text) {
                return this.messaging.publicLivechatGlobal.options.button_text;
            }
            return this.env._t("Chat with one of our collaborators");
        },
        /**
         * @returns {string}
         */
        _computeButtonTextColor() {
            return this.messaging.publicLivechatGlobal.options.button_text_color;
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeChannelId() {
            return this.messaging.publicLivechatGlobal.options.channel_id;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChatbot() {
            if (this.isTestChatbot) {
                return insertAndReplace({ data: this.testChatbotData.chatbot });
            }
            if (this.chatbotState === 'init') {
                return insertAndReplace({ data: this.rule.chatbot });
            }
            if (this.chatbotState === 'welcome') {
                return insertAndReplace({ data: this.livechatInit.rule.chatbot });
            }
            if (this.chatbotState === 'restore_session' && this.localStorageChatbotState) {
                return insertAndReplace({ data: this.localStorageChatbotState._chatbot });
            }
            return clear();
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
         * @returns {string|FieldCommand}
         */
        _computeChatbotState() {
            if (this.rule && !!this.rule.chatbot) {
                return 'init';
            }
            if (this.livechatInit && this.livechatInit.rule.chatbot) {
                return 'welcome';
            }
            return clear();
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeCurrentPartnerId() {
            if (!this.messaging.publicLivechatGlobal.isAvailable) {
                return clear();
            }
            return this.messaging.publicLivechatGlobal.options.current_partner_id;
        },
        /**
        * @private
        * @returns {string}
        */
        _computeDefaultMessage() {
            if (this.messaging.publicLivechatGlobal.options.default_message) {
                return this.messaging.publicLivechatGlobal.options.default_message;
            }
            return this.env._t("How may I help you?");
        },
        /**
         * @private
         * @returns {string}
         */
        _computeDefaultUsername() {
            if (this.messaging.publicLivechatGlobal.options.default_username) {
                return this.messaging.publicLivechatGlobal.options.default_username;
            }
            return this.env._t("Visitor");
        },
        /**
         * @private
         * @returns {string}
         */
        _computeHeaderBackgroundColor() {
            return this.messaging.publicLivechatGlobal.options.header_background_color;
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
            if (this.messaging.publicLivechatGlobal.options.input_placeholder) {
                return this.messaging.publicLivechatGlobal.options.input_placeholder;
            }
            return this.env._t("Ask something ...");
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsChatbot() {
            if (this.isTestChatbot) {
                return true;
            }
            if (this.rule && this.rule.chatbot) {
                return true;
            }
            if (this.livechatInit && this.livechatInit.rule.chatbot) {
                return true;
            }
            if (this.chatbotState === 'welcome') {
                return true;
            }
            if (this.localStorageChatbotState) {
                return true;
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeLocalStorageChatbotState() {
            if (!this.sessionCookie) {
                return clear();
            }
            const data = localStorage.getItem(this.chatbotSessionCookieKey);
            if (!data) {
                return clear();
            }
            return JSON.parse(data);
        },
        /**
         * @private
         * @returns {string}
         */
        _computeServerUrl() {
            if (this.isChatbot) {
                return this.messaging.publicLivechatGlobal.chatbotServerUrl;
            }
            return this.messaging.publicLivechatGlobal.serverUrl;
        },
        /**
         * @returns {string|FieldCommand}
         */
        _computeChatbotSessionCookieKey() {
            if (!this.sessionCookie) {
                return clear();
            }
            return 'im_livechat.chatbot.state.uuid_' + JSON.parse(this.sessionCookie).uuid;
        },
        /**
         * @private
         * @returns {string}
         */
        _computeTitleColor() {
            return this.messaging.publicLivechatGlobal.options.title_color;
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
        channelId: attr({
            compute: '_computeChannelId',
        }),
        chatbot: one('Chatbot', {
            compute: '_computeChatbot',
            inverse: 'livechatButtonViewOwner',
            isCausal: true,
        }),
        chatbotNextStepTimeout: attr(),
        chatbotSessionCookieKey: attr({
            compute: '_computeChatbotSessionCookieKey',
        }),
        chatbotState: attr({
            compute: '_computeChatbotState',
        }),
        chatbotWelcomeMessageTimeout: attr(),
        chatWindow: one('PublicLivechatWindow', {
            inverse: 'livechatButtonViewOwner',
            isCausal: true,
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
            compute: '_computeIsChatbot',
            default: false,
        }),
        isChatbotRedirecting: attr({
            default: false,
        }),
        isOpeningChat: attr({
            default: false,
        }),
        isTestChatbot: attr({
            default: false,
        }),
        isTypingTimeout: attr(),
        isWebsiteLivechatChatbotFlow: attr({
            default: false,
        }),
        livechatInit: attr(),
        localStorageChatbotState: attr({
            compute: '_computeLocalStorageChatbotState',
        }),
        messages: many('PublicLivechatMessage'),
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            inverse: 'livechatButtonView',
            readonly: true,
            required: true,
        }),
        rule: attr(),
        serverUrl: attr({
            compute: '_computeServerUrl',
        }),
        sessionCookie: attr(),
        testChatbotData: attr(),
        titleColor: attr({
            compute: '_computeTitleColor',
        }),
        widget: attr(),
    },
});
