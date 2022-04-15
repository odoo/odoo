/** @odoo-module alias=website_livechat.chatbot_test_script **/

import publicWidget from 'web.public.widget';
import utils from 'web.utils';

import LivechatButton from 'im_livechat.legacy.im_livechat.LivechatButton';
import WebsiteLivechat from 'im_livechat.legacy.im_livechat.model.WebsiteLivechat';

/**
 * Override of the LivechatButton to create a testing environment for the chatbot script.
 *
 * The biggest difference here is that we don't have a 'im_livechat.channel' to work with.
 * The 'mail.channel' holding the conversation between the bot and the testing user has been created
 * by the 'chatbot/<model("chatbot.script"):chatbot>/test' endpoint.
 */
const LivechatButtonTestChatbot = LivechatButton.extend({
    /**
     * Initialize various data received from the 'chatbot_test_script_page' template.
     */
    init: function (parent, chatbotData) {
        this._super(...arguments);

        this._rule = {
            'action': 'auto_popup',
            'auto_popup_timer': 0,
        };
        this._chatbot = chatbotData.chatbot;
        this._chatbotCurrentStep = this._chatbot.chatbot_welcome_steps[
            this._chatbot.chatbot_welcome_steps.length - 1];
        this._channelData = chatbotData.channel;
        this._isChatbot = true;
        this._serverURL = chatbotData.serverUrl;

        this.options.input_placeholder = '';
    },

    /**
     * Overridden to avoid calling the "init" endpoint as it requires a im_livechat.channel linked
     * to work properly.
     *
     * @override
     */
    willStart: function () {
        return this._loadQWebTemplate();
    },

    /**
     * Overridden to avoid calling the "get_session" endpoint as it requires a im_livechat.channel
     * linked to work properly.
     *
     * Here, we already have a mail.channel created (see 'website_livechat_chatbot_test_script') so we
     * use its configuration to create the 'WebsiteLivechat' Widget.
     *
     * @private
     * @override
     */
    _openChat: function () {
        this._livechat = new WebsiteLivechat({
            parent: this,
            data: this._channelData,
        });

        return this._openChatWindow().then(() => {
            this._sendWelcomeMessage();
            this._renderMessages();
            this.call('bus_service', 'addChannel', this._livechat.getUUID());
            this.call('bus_service', 'startPolling');
            utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(this._livechat.toData()), true), 60 * 60);
            this._openingChat = false;
        });
    },
});

publicWidget.registry.livechatChatbotTestScript = publicWidget.Widget.extend({
    selector: '.o_livechat_js_chatbot_test_script',

    /**
     * Remove any existing session cookie to start fresh
     */
    start: function () {
        utils.set_cookie('im_livechat_session', '', -1);
        utils.set_cookie('im_livechat_auto_popup', '', -1);
        utils.set_cookie('im_livechat_history', '', -1);
        utils.set_cookie('im_livechat_previous_operator_pid', '', -1);

        return this._super(...arguments).then(() => {
            this.livechatButton = new LivechatButtonTestChatbot(this, this.$el.data());
            this.livechatButton.appendTo(document.body);
        });
    }
});
