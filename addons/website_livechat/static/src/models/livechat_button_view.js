/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
import { insertAndReplace } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@im_livechat/models/livechat_button_view';

import { set_cookie, unaccent } from 'web.utils';

patchRecordMethods('LivechatButtonView', {
    /**
     * Check if a chat request is opened for this visitor
     * if yes, replace the session cookie and start the conversation immediately.
     * Do this before calling super to have everything ready before executing existing start logic.
     * This is used for chat request mechanism, when an operator send a chat request
     * from backend to a website visitor.
     *
     * @override
     */
    willStart: function () {
        if (this.isTestChatbot) {
            /**
             * Overridden to avoid calling the "init" endpoint as it requires a im_livechat.channel linked
             * to work properly.
             */
            return this.messaging.publicLivechatGlobal.loadQWebTemplate();
        }
        if (this.messaging.publicLivechatGlobal.options.chat_request_session) {
            set_cookie('im_livechat_session', JSON.stringify(this.messaging.publicLivechatGlobal.options.chat_request_session), 60 * 60);
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeIsOpenChatDebounced() {
        if (this.isTestChatbot) {
            return false;
        }
        return this._super();
    },
    /**
     * Overridden to avoid calling the "get_session" endpoint as it requires a im_livechat.channel
     * linked to work properly.
     *
     * Here, we already have a mail.channel created (see 'website_livechat_chatbot_test_script') so we
     * use its configuration to create the 'WebsiteLivechat' Widget.
     *
     * @override
     */
    async _openChat() {
        if (!this.isTestChatbot) {
            return this._super();
        }
        this.messaging.publicLivechatGlobal.update({
            publicLivechat: insertAndReplace({ data: this.testChatbotData.channel }),
        });
        await this.openChatWindow();
        this.widget._sendWelcomeMessage();
        this.widget._renderMessages();
        this.env.services.bus_service.addChannel(this.messaging.publicLivechatGlobal.publicLivechat.uuid);
        this.env.services.bus_service.startPolling();
        set_cookie('im_livechat_session', unaccent(JSON.stringify(this.messaging.publicLivechatGlobal.publicLivechat.legacyPublicLivechat.toData()), true), 60 * 60);
        this.update({ isOpeningChat: false });
    },
});
