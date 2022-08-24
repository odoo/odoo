/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import { qweb } from 'web.core';

import { get_cookie, Markup, set_cookie } from 'web.utils';

registerModel({
    name: 'PublicLivechatGlobal',
    lifecycleHooks: {
        _created() {
            // History tracking
            const page = window.location.href.replace(/^.*\/\/[^/]+/, '');
            const pageHistory = get_cookie(this.LIVECHAT_COOKIE_HISTORY);
            let urlHistory = [];
            if (pageHistory) {
                urlHistory = JSON.parse(pageHistory) || [];
            }
            if (!_.contains(urlHistory, page)) {
                urlHistory.push(page);
                while (urlHistory.length > this.HISTORY_LIMIT) {
                    urlHistory.shift();
                }
                set_cookie(this.LIVECHAT_COOKIE_HISTORY, JSON.stringify(urlHistory), 60 * 60 * 24); // 1 day cookie
            }
            this.willStart();
        },
    },
    recordMethods: {
        async loadQWebTemplate() {
            const templates = await this.messaging.rpc({ route: '/im_livechat/load_templates' });
            for (const template of templates) {
                qweb.add_template(template);
            }
            this.update({ hasLoadedQWebTemplate: true });
        },
        async willStart() {
            await this._willStart();
            await this._willStartChatbot();
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeChannelId() {
            return this.options.channel_id;
        },
        /**
         * Compares the last message of the conversation to this livechat's operator id.
         *
         * @private
         * @returns {boolean}
         */
        _computeIsLastMessageFromCustomer() {
            if (!this.lastMessage) {
                return clear();
            }
            if (!this.publicLivechat) {
                return clear();
            }
            return this.lastMessage.authorId !== this.publicLivechat.operator.id;
        },
        /**
          * @private
          * @returns {FieldCommand}
          */
         _computeLastMessage() {
            if (this.messages.length === 0) {
                return clear();
            }
            return this.messages[this.messages.length - 1];
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeLivechatButtonView() {
            if (this.isAvailable && this.isAvailableForMe && this.hasLoadedQWebTemplate && this.env.services.public_livechat_service) {
                return {};
            }
            return clear();
        },
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
                this.update({ isAvailableForMe: true });
            } else {
                const result = await this.messaging.rpc({
                    route: '/im_livechat/init',
                    params: { channel_id: this.channelId },
                });
                if (result.available_for_me) {
                    this.update({ isAvailableForMe: true });
                }
                this.update({ rule: result.rule });
            }
            return this.loadQWebTemplate();
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
         * @override
         */
        async _willStartChatbot() {
            if (this.rule) {
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
                }
            }

            if (this.chatbot.state === 'init') {
                // we landed on a website page where a channel rule is configured to run a chatbot.script
                // -> initialize necessary state
                if (this.rule.chatbot_welcome_steps && this.rule.chatbot_welcome_steps.length !== 0) {
                    this.chatbot.update({
                        currentStep: {
                            data: this.chatbot.lastWelcomeStep,
                        },
                    });
                }
            } else if (this.chatbot.state === 'welcome') {
                // we landed on a website page and a chatbot script was initialized on a previous one
                // however the end-user did not interact with the bot ( :( )
                // -> remove cookie to force opening the popup again
                // -> initialize necessary state
                // -> batch welcome message (see '_sendWelcomeChatbotMessage')
                set_cookie('im_livechat_auto_popup', '', -1);
                this.update({ history: clear() });
                this.update({ rule: this.livechatInit.rule });
            } else if (this.chatbot.state === 'restore_session') {
                // we landed on a website page and a chatbot script is currently running
                // -> restore the user's session (see 'Chatbot/restoreSession')
                this.chatbot.restoreSession();
            }
        },
    },
    fields: {
        HISTORY_LIMIT: attr({
            default: 15,
        }),
        LIVECHAT_COOKIE_HISTORY: attr({
            default: 'im_livechat_history',
        }),
        RATING_TO_EMOJI: attr({
            default: {
                5: "😊",
                3: "😐",
                1: "😞",
            },
        }),
        channelId: attr({
            compute: '_computeChannelId',
        }),
        chatbot: one('Chatbot', {
            default: {},
            inverse: 'publicLivechatGlobalOwner',
            isCausal: true,
        }),
        chatWindow: one('PublicLivechatWindow', {
            inverse: 'publicLivechatGlobalOwner',
            isCausal: true,
        }),
        feedbackView: one('PublicLivechatFeedbackView', {
            inverse: 'publicLivechatGlobalOwner',
            isCausal: true,
        }),
        hasLoadedQWebTemplate: attr({
            default: false,
        }),
        history: attr({
            default: null,
        }),
        isAvailable: attr({
            default: false,
        }),
        isAvailableForMe: attr({
            default: false,
        }),
        isLastMessageFromCustomer: attr({
            compute: '_computeIsLastMessageFromCustomer',
            default: false,
        }),
        isTestChatbot: attr({
            default: false,
        }),
        lastMessage: one('PublicLivechatMessage', {
            compute: '_computeLastMessage',
        }),
        livechatButtonView: one('LivechatButtonView', {
            compute: '_computeLivechatButtonView',
            inverse: 'publicLivechatGlobalOwner',
            isCausal: true,
        }),
        livechatInit: attr(),
        messages: many('PublicLivechatMessage'),
        notificationHandler: one('PublicLivechatGlobalNotificationHandler', {
            inverse: 'publicLivechatGlobalOwner',
            isCausal: true,
        }),
        options: attr({
            default: {},
        }),
        publicLivechat: one('PublicLivechat', {
            inverse: 'publicLivechatGlobalOwner',
            isCausal: true,
        }),
        rule: attr(),
        serverUrl: attr({
            default: '',
        }),
        sessionCookie: attr(),
        testChatbotData: attr(),
    },
});
