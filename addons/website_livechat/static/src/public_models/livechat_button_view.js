/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { clear } from '@mail/model/model_field_command';

import {unaccent} from 'web.utils';
import {setCookie} from 'web.utils.cookies';

registerPatch({
    name: 'LivechatButtonView',
    recordMethods: {
        /**
         * Small override that removes current messages when restarting.
         * This allows to easily check for new posted messages without having
         * the old ones "polluting" the thread and making it hard to write
         * proper jQuery selectors in the tour.
         *
         * @override
         */
        async onChatbotRestartScript(ev) {
            if (this.global.PublicLivechatGlobal.chatbot.isWebsiteLivechatTourFlow) {
                this.global.PublicLivechatGlobal.update({ messages: clear() });
                this.global.PublicLivechatGlobal.chatWindow.renderMessages();
            }
            return this._super(ev);
        },
        /**
         * Overridden to avoid calling the "get_session" endpoint as it requires
         * a im_livechat.channel linked to work properly.
         *
         * Here, we already have a mail.channel created (see
         * 'website_livechat_chatbot_test_script') so we use its configuration
         * to create the 'WebsiteLivechat' Widget.
         *
         * @override
         */
        async _openChat() {
            if (!this.global.PublicLivechatGlobal.isTestChatbot) {
                return this._super();
            }
            this.global.PublicLivechatGlobal.update({
                publicLivechat: { data: this.global.PublicLivechatGlobal.testChatbotData.channel },
            });
            await this.openChatWindow();
            this.widget._sendWelcomeMessage();
            this.global.PublicLivechatGlobal.chatWindow.renderMessages();
            this.env.services.bus_service.addChannel(this.global.PublicLivechatGlobal.publicLivechat.uuid);
            setCookie('im_livechat_session', unaccent(JSON.stringify(this.global.PublicLivechatGlobal.publicLivechat.widget.toData()), true), 60 * 60, 'required');
            this.update({ isOpeningChat: false });
        },
    },
    fields: {
        isOpenChatDebounced: {
            compute() {
                if (this.global.PublicLivechatGlobal.isTestChatbot) {
                    return false;
                }
                return this._super();
            },
        },
    },
});
