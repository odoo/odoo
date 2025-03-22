/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

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
            if (this.messaging.publicLivechatGlobal.chatbot.isWebsiteLivechatTourFlow) {
                this.messaging.publicLivechatGlobal.update({ messages: clear() });
                this.messaging.publicLivechatGlobal.chatWindow.renderMessages();
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
            if (!this.messaging.publicLivechatGlobal.isTestChatbot) {
                return this._super();
            }
            this.messaging.publicLivechatGlobal.update({
                publicLivechat: { data: this.messaging.publicLivechatGlobal.options.testChatbotChannelData },
            });
            await this.openChatWindow();
            this.widget._sendWelcomeMessage();
            this.messaging.publicLivechatGlobal.chatWindow.renderMessages();
            this.env.services.bus_service.addChannel(this.messaging.publicLivechatGlobal.publicLivechat.uuid);
            setCookie('im_livechat_session', encodeURIComponent(JSON.stringify(this.messaging.publicLivechatGlobal.publicLivechat.widget.toData()), true), 60 * 60, 'required');
            this.update({ isOpeningChat: false });
        },
    },
    fields: {
        floatingTextView: one('PublicLivechatFloatingTextView', {
            inverse: 'livechatButtonViewOwner',
        }),
        hasFloatingText: attr({
            compute() {
                return Boolean(
                    this.messaging.publicLivechatGlobal.rule &&
                    this.messaging.publicLivechatGlobal.rule.action === 'display_button_and_text' &&
                    this.isWidgetMounted
                );
            },
        }),
        initialFloatingTextViewVisibilityTimer: one('Timer', {
            compute() {
                if (!this.floatingTextView && this.hasFloatingText) {
                    return {};
                }
                return clear();
            },
            inverse: 'livechatButtonViewOwnerAsInitialFloatingTextVisibility',
        }),
        isOpenChatDebounced: {
            compute() {
                if (this.messaging.publicLivechatGlobal.isTestChatbot) {
                    return false;
                }
                return this._super();
            },
        },
    },
});
