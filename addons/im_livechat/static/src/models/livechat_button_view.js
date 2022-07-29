/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

import { get_cookie, Markup, set_cookie } from 'web.utils';

registerModel({
    name: 'LivechatButtonView',
    identifyingFields: ['publicLivechatGlobalOwner'],
    recordMethods: {
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
            let chatbotState = localStorage.getItem(this.chatbotSessionCookieKey);
            if (chatbotState) {
                this.chatbot.update({ currentStep: insertAndReplace({ data: this.localStorageChatbotState._chatbotCurrentStep }) });
            }
        },
        async willStart() {
            try {
                await this._willStart();
            } finally {
                await this._willStartChatbot();
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
        /**
         * @private
         */
        async _willStart() {
            const cookie = get_cookie('im_livechat_session');
            if (cookie) {
                const channel = JSON.parse(cookie);
                const history = await this.messaging.rpc({
                    route: '/mail/chat_history',
                    params: { uuid: channel.uuid, limit: 100 },
                });
                history.reverse();
                this.update({ history });
                for (const message of this.history) {
                    message.body = Markup(message.body);
                }
            } else {
                const result = await this.messaging.rpc({
                    route: '/im_livechat/init',
                    params: { channel_id: this.channelId },
                });
                if (!result.available_for_me) {
                    return Promise.reject();
                }
                this.update({ rule: result.rule });
            }
            return this.messaging.publicLivechatGlobal.loadQWebTemplate();
        },
        /**
         * This override handles the following use cases:
         *
         * - If the chat is started for the first time (first visit of a visitor)
         *   We register the chatbot configuration and the rest of the behavior is triggered by various
         *   method overrides ('sendWelcomeMessage', 'sendMessage', ...)
         *
         * - If the chat has been started before, but the user did not interact with the bot
         *   The default behavior is to open an empty chat window, without any messages.
         *   In addition, we fetch the configuration (with a '/init' call), to see if we have a bot
         *   configured.
         *   Indeed we want to trigger the bot script on every page where the associated rule is matched.
         *
         * - If we have a non-empty chat history, resume the chat script where the end-user left it by
         *   fetching the necessary information from the local storage.
         *
         * @private
         */
        async _willStartChatbot() {
            if (this.rule && !!this.rule.chatbot) {
                // noop
            } else if (this.history !== null && this.history.length === 0) {
                this.update({
                    livechatInit: await this.messaging.rpc({
                        route: '/im_livechat/init',
                        params: { channel_id: this.channelId },
                    }),
                });
            } else if (this.history !== null && this.history.length !== 0) {
                const sessionCookie = get_cookie('im_livechat_session');
                if (sessionCookie) {
                    this.update({ sessionCookie });
                    if (localStorage.getItem(this.chatbotSessionCookieKey)) {
                        this.update({ chatbotState: 'restore_session' });
                    }
                }
            }
    
            if (this.chatbotState === 'init') {
                // we landed on a website page where a channel rule is configured to run a chatbot.script
                // -> initialize necessary state
                if (this.rule.chatbot_welcome_steps && this.rule.chatbot_welcome_steps.length !== 0) {
                    this.chatbot.update({
                        currentStep: insertAndReplace({
                            data: this.chatbot.lastWelcomeStep,
                        }),
                    });
                }
            } else if (this.chatbotState === 'welcome') {
                // we landed on a website page and a chatbot script was initialized on a previous one
                // however the end-user did not interact with the bot ( :( )
                // -> remove cookie to force opening the popup again
                // -> initialize necessary state
                // -> batch welcome message (see '_sendWelcomeChatbotMessage')
                set_cookie('im_livechat_auto_popup', '', -1);
                this.update({ history: clear() });
                this.update({ rule: this.livechatInit.rule });
            } else if (this.chatbotState === 'restore_session') {
                // we landed on a website page and a chatbot script is currently running
                // -> restore the user's session (see 'chatbotRestoreSession')
                this.chatbotRestoreSession();
            }
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
        chatbotSessionCookieKey: attr({
            compute: '_computeChatbotSessionCookieKey',
        }),
        chatbotState: attr({
            compute: '_computeChatbotState',
        }),
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
