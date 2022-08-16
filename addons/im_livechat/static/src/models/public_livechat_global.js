/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

import { qweb } from 'web.core';
import utils from 'web.utils';

registerModel({
    name: 'PublicLivechatGlobal',
    identifyingFields: ['messaging'],
    lifecycleHooks: {
        _created() {
            // History tracking
            const page = window.location.href.replace(/^.*\/\/[^/]+/, '');
            const pageHistory = utils.get_cookie(this.LIVECHAT_COOKIE_HISTORY);
            let urlHistory = [];
            if (pageHistory) {
                urlHistory = JSON.parse(pageHistory) || [];
            }
            if (!_.contains(urlHistory, page)) {
                urlHistory.push(page);
                while (urlHistory.length > this.HISTORY_LIMIT) {
                    urlHistory.shift();
                }
                utils.set_cookie(this.LIVECHAT_COOKIE_HISTORY, JSON.stringify(urlHistory), 60 * 60 * 24); // 1 day cookie
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
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChatbot() {
            if (!this.livechatButtonView) {
                return clear();
            }
            if (this.livechatButtonView.isTestChatbot) {
                return insertAndReplace({ data: this.livechatButtonView.testChatbotData.chatbot });
            }
            if (this.livechatButtonView.chatbotState === 'init') {
                return insertAndReplace({ data: this.livechatButtonView.rule.chatbot });
            }
            if (this.livechatButtonView.chatbotState === 'welcome') {
                return insertAndReplace({ data: this.livechatButtonView.livechatInit.rule.chatbot });
            }
            if (this.livechatButtonView.chatbotState === 'restore_session' && this.livechatButtonView.localStorageChatbotState) {
                return insertAndReplace({ data: this.livechatButtonView.localStorageChatbotState._chatbot });
            }
            return clear();
        },
        /**
          * @private
          * @returns {FieldCommand}
          */
         _computeLastMessage() {
            if (this.messages.length === 0) {
                return clear();
            }
            return replace(this.messages[this.messages.length - 1]);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeLivechatButtonView() {
            if (this.isAvailable && this.hasLoadedQWebTemplate && this.env.services.public_livechat_service) {
                return insertAndReplace();
            }
            return clear();
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
        chatbot: one('Chatbot', {
            compute: '_computeChatbot',
            inverse: 'publicLivechatGlobalOwner',
            isCausal: true,
        }),
        chatbotServerUrl: attr(),
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
        lastMessage: one('PublicLivechatMessage', {
            compute: '_computeLastMessage',
        }),
        livechatButtonView: one('LivechatButtonView', {
            compute: '_computeLivechatButtonView',
            inverse: 'publicLivechatGlobalOwner',
            isCausal: true,
        }),
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
        serverUrl: attr({
            default: '',
        }),
    },
});
