/** @odoo-module alias=website_livechat.chatbot_test_script **/

import publicWidget from 'web.public.widget';
import utils from 'web.utils';

import LivechatButton from '@im_livechat/legacy/widgets/livechat_button';
import WebsiteLivechat from '@im_livechat/legacy/models/website_livechat';

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
    init: function (parent, messaging, chatbotData) {
        this._super(...arguments);

        this.messaging.livechatButtonView.update({
            rule: {
                'action': 'auto_popup',
                'auto_popup_timer': 0,
            },
        });
        this.messaging.livechatButtonView.update({ chatbot: chatbotData.chatbot });
        this._chatbotCurrentStep = this.messaging.livechatButtonView.chatbot.chatbot_welcome_steps[
            this.messaging.livechatButtonView.chatbot.chatbot_welcome_steps.length - 1];
        this._channelData = chatbotData.channel;
        this.messaging.livechatButtonView.update({ isChatbot: true });
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
        this.messaging.livechatButtonView.update({
            livechat: new WebsiteLivechat({
                parent: this,
                data: this._channelData,
            }),
        });

        return this._openChatWindow().then(() => {
            this._sendWelcomeMessage();
            this._renderMessages();
            this.call('bus_service', 'addChannel', this.messaging.livechatButtonView.livechat.getUUID());
            this.call('bus_service', 'startPolling');
            utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(this.messaging.livechatButtonView.livechat.toData()), true), 60 * 60);
            this.messaging.livechatButtonView.update({ isOpeningChat: false });
        });
    },
});

publicWidget.registry.livechatChatbotTestScript = publicWidget.Widget.extend({
    selector: '.o_livechat_js_chatbot_test_script',
    init(parent) {
        this._super(...arguments);
        this.env = parent.env;
    },
    /**
     * Remove any existing session cookie to start fresh
     */
    async start() {
        utils.set_cookie('im_livechat_session', '', -1);
        utils.set_cookie('im_livechat_auto_popup', '', -1);
        utils.set_cookie('im_livechat_history', '', -1);
        utils.set_cookie('im_livechat_previous_operator_pid', '', -1);
        const messaging = this.env.services.messaging.get();
        return this._super(...arguments).then(() => {
            messaging.update({
                isInPublicLivechat: true,
                isPublicLivechatAvailable: true,
                publicLivechatServerUrlChatbot: this.$el.data().serverUrl,
            });
            this.livechatButton = new LivechatButtonTestChatbot(this, messaging, this.$el.data());
            this.livechatButton.appendTo(document.body);
        });
    }
});
