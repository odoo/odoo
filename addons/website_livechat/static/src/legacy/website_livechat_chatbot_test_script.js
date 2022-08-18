/** @odoo-module alias=website_livechat.chatbot_test_script **/

import publicWidget from 'web.public.widget';
import utils from 'web.utils';

import LivechatButton from '@im_livechat/legacy/widgets/livechat_button';

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

        this.messaging.publicLivechatGlobal.livechatButtonView.update({
            rule: {
                'action': 'auto_popup',
                'auto_popup_timer': 0,
            },
        });
        this.messaging.publicLivechatGlobal.update({ isTestChatbot: true });
        this.messaging.publicLivechatGlobal.livechatButtonView.update({ testChatbotData: chatbotData.chatbot });
        this.messaging.publicLivechatGlobal.chatbot.update({
            currentStep: {
                data: this.messaging.publicLivechatGlobal.chatbot.lastWelcomeStep,
            },
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
        const messaging = await this.env.services.messaging.get();
        return this._super(...arguments).then(() => {
            messaging.update({
                publicLivechatGlobal: { isAvailable: true, chatbotServerUrl: this.$el.data().serverUrl },
            });
            this.livechatButton = new LivechatButtonTestChatbot(this, messaging, this.$el.data());
            this.livechatButton.appendTo(document.body);
        });
    }
});
