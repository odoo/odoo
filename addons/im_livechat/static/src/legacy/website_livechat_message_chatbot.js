/** @odoo-module **/

import WebsiteLivechatMessage from '@im_livechat/legacy/models/website_livechat_message';

/**
 * Override of the WebsiteLivechatMessage that includes chatbot capabilities.
 * The main changes are:
 * - Allow to display options for the end-user to click on ("_chatbotStepAnswers")
 * - Show a different name/icon for the chatbot (instead of the 'OdooBot' operator name/icon)
 */
WebsiteLivechatMessage.include({
    /**
     * @param {@im_livechat/legacy/widgets/livechat_button} parent
     * @param {Object} data
     * @param {Object} options
     * @param {string} options.default_username
     * @param {string} options.serverURL
     */
    init(parent, data, options) {
        this._super(...arguments);

        if (parent.messaging.livechatButtonView.isChatbot) {
            this._chatbotStepId = data.chatbot_script_step_id;
            this._chatbotStepAnswers = data.chatbot_step_answers;
            this._chatbotStepAnswerId = data.chatbot_selected_answer_id;
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get chat bot script step ID
     *
     * @return {string}
     */
    getChatbotStepId() {
        return this._chatbotStepId;
    },
    /**
     * Get chat bot script answers
     *
     * @return {string}
     */
    getChatbotStepAnswers() {
        return this._chatbotStepAnswers;
    },
    /**
     * Get chat bot script answer ID
     *
     * @return {string}
     */
    getChatbotStepAnswerId() {
        return this._chatbotStepAnswerId;
    },
    /**
     * @override
     */
    setChatbotStepAnswerId(chatbotStepAnswerId) {
        this._chatbotStepAnswerId = chatbotStepAnswerId;
    }
});

export default WebsiteLivechatMessage;
