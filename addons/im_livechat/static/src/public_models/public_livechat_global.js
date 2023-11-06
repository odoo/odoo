/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import { session } from "@web/session";

import { qweb } from 'web.core';
import { Markup } from 'web.utils';
import {getCookie, setCookie, deleteCookie} from 'web.utils.cookies';

registerModel({
    name: 'PublicLivechatGlobal',
    lifecycleHooks: {
        _created() {
            // History tracking
            const page = window.location.href.replace(/^.*\/\/[^/]+/, '');
            const pageHistory = getCookie(this.LIVECHAT_COOKIE_HISTORY);
            let urlHistory = [];
            if (pageHistory) {
                urlHistory = JSON.parse(pageHistory) || [];
            }
            if (!_.contains(urlHistory, page)) {
                urlHistory.push(page);
                while (urlHistory.length > this.HISTORY_LIMIT) {
                    urlHistory.shift();
                }
                setCookie(this.LIVECHAT_COOKIE_HISTORY, JSON.stringify(urlHistory), 60 * 60 * 24, 'optional'); // 1 day cookie
            }
            if (this.isAvailable) {
                this.willStart();
            }
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
        async _willStart() {
            const strCookie = getCookie('im_livechat_session');
            let isSessionCookieAvailable = Boolean(strCookie);
            let cookie = JSON.parse(strCookie || '{}');
            if (isSessionCookieAvailable && cookie.visitor_uid !== session.user_id) {
                this.leaveSession();
                isSessionCookieAvailable = false;
                cookie = {};
            }
            if (cookie.id) {
                const history = await this.messaging.rpc({
                    route: '/mail/chat_history',
                    params: { uuid: cookie.uuid, limit: 100 },
                });
                history.reverse();
                this.update({ history });
                for (const message of this.history) {
                    message.body = Markup(message.body);
                }
                this.update({ isAvailableForMe: true });
            } else if (isSessionCookieAvailable) {
                this.update({ history: [], isAvailableForMe: true });
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
                const sessionCookie = getCookie('im_livechat_session');
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
                deleteCookie('im_livechat_auto_popup');
                this.update({ history: clear() });
                this.update({ rule: this.livechatInit.rule });
            } else if (this.chatbot.state === 'restore_session') {
                // we landed on a website page and a chatbot script is currently running
                // -> restore the user's session (see 'Chatbot/restoreSession')
                this.chatbot.restoreSession();
            }
        },

        getVisitorUserId() {
            const cookie = JSON.parse(getCookie("im_livechat_session") || "{}");
            if ("visitor_uid" in cookie) {
                return cookie.visitor_uid;
            }
            return session.user_id;
        },

        /**
         * Called when the visitor leaves the livechat chatter the first time (first click on X button)
         * this will deactivate the mail_channel, notify operator that visitor has left the channel.
         */
        leaveSession() {
            const cookie = getCookie('im_livechat_session');
            if (cookie) {
                const channel = JSON.parse(cookie);
                if (channel.uuid) {
                    this.messaging.rpc({ route: '/im_livechat/visitor_leave_session', params: { uuid: channel.uuid } });
                }
                deleteCookie('im_livechat_session');
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
            compute() {
                return this.options.channel_id;
            },
        }),
        chatbot: one('Chatbot', {
            default: {},
            inverse: 'publicLivechatGlobalOwner',
        }),
        chatWindow: one('PublicLivechatWindow', {
            inverse: 'publicLivechatGlobalOwner',
        }),
        feedbackView: one('PublicLivechatFeedbackView', {
            inverse: 'publicLivechatGlobalOwner',
        }),
        hasLoadedQWebTemplate: attr({
            default: false,
        }),
        hasWebsiteLivechatFeature: attr({
            compute() {
                return false;
            },
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
            /**
             * Compares the last message of the conversation to this livechat's operator id.
             */
            compute() {
                if (!this.lastMessage) {
                    return clear();
                }
                if (!this.publicLivechat) {
                    return clear();
                }
                if (!this.publicLivechat.operator) {
                    return clear();
                }
                return this.lastMessage.authorId !== this.publicLivechat.operator.id;
            },
            default: false,
        }),
        isTestChatbot: attr({
            compute() {
                if (!this.options) {
                    return clear();
                }
                return Boolean(this.options.isTestChatbot);
            },
            default: false,
        }),
        lastMessage: one('PublicLivechatMessage', {
            compute() {
                if (this.messages.length === 0) {
                    return clear();
                }
                return this.messages[this.messages.length - 1];
            },
        }),
        livechatButtonView: one('LivechatButtonView', {
            compute() {
                if (this.isAvailable && (this.isAvailableForMe || this.isTestChatbot) && this.hasLoadedQWebTemplate && this.env.services.public_livechat_service) {
                    return {};
                }
                return clear();
            },
            inverse: 'publicLivechatGlobalOwner',
        }),
        livechatInit: attr(),
        messages: many('PublicLivechatMessage'),
        notificationHandler: one('PublicLivechatGlobalNotificationHandler', {
            inverse: 'publicLivechatGlobalOwner',
            compute() {
                if (this.publicLivechat && !this.publicLivechat.isTemporary) {
                    return {};
                }
                return clear();
            }
        }),
        options: attr({
            default: {},
        }),
        publicLivechat: one('PublicLivechat', {
            inverse: 'publicLivechatGlobalOwner',
        }),
        rule: attr(),
        serverUrl: attr({
            default: '',
        }),
        sessionCookie: attr(),
        testChatbotData: attr({
            compute() {
                if (!this.options) {
                    return clear();
                }
                return this.options.testChatbotData;
            },
        }),
        welcomeMessages: many('PublicLivechatMessage', {
            compute() {
                return this.messages.filter((message) => {
                    return message.id && typeof message.id === 'string' && message.id.startsWith('_welcome_');
                });
            },
        }),
    },
});
