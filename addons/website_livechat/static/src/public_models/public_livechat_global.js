/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

import { deleteCookie, setCookie } from 'web.utils.cookies';

registerPatch({
    name: 'PublicLivechatGlobal',
    recordMethods: {
        /**
         * Check if a chat request is opened for this visitor
         * if yes, replace the session cookie and start the conversation
         * immediately. Do this before calling super to have everything ready
         * before executing existing start logic. This is used for chat request
         * mechanism, when an operator send a chat request from backend to a
         * website visitor.
         *
         * @override
         */
        willStart() {
            if (this.isTestChatbot) {
                /**
                 * Override of the LivechatButton to create a testing environment for the chatbot script.
                 *
                 * The biggest difference here is that we don't have a 'im_livechat.channel' to work with.
                 * The 'mail.channel' holding the conversation between the bot and the testing user has been created
                 * by the 'chatbot/<model("chatbot.script"):chatbot>/test' endpoint.
                 */
                deleteCookie('im_livechat_session');
                deleteCookie('im_livechat_auto_popup');
                deleteCookie('im_livechat_history');
                deleteCookie('im_livechat_previous_operator_pid');
                this.update({
                    rule: {
                        'action': 'auto_popup',
                        'auto_popup_timer': 0,
                    },
                });
                this.chatbot.update({
                    currentStep: {
                        data: this.chatbot.lastWelcomeStep,
                    },
                });
                /**
                 * Overridden to avoid calling the "init" endpoint as it
                 * requires a im_livechat.channel linked to work properly.
                 */
                return this.loadQWebTemplate();
            }
            if (this.options.chat_request_session) {
                this.options.chat_request_session.visitor_uid = this.getVisitorUserId();
                setCookie('im_livechat_session', JSON.stringify(this.options.chat_request_session), 60 * 60, 'required');
            }
            return this._super();
        },
    },
    fields: {
        hasWebsiteLivechatFeature: {
            compute() {
                return true;
            },
        },
    },
});
