/** @odoo-module **/

import WebsiteLivechatMessage from 'im_livechat.legacy.im_livechat.model.WebsiteLivechatMessage';

/**
 * Override of the WebsiteLivechatMessage that includes chatbot capabilities.
 * The main changes are:
 * - Allow to display options for the end-user to click on ("_chatbotStepAnswers")
 * - Show a different name/icon for the chatbot (instead of the 'OdooBot' operator name/icon)
 */
WebsiteLivechatMessage.include({
    /**
     * @param {im_livechat.legacy.im_livechat.im_livechat.LivechatButton} parent
     * @param {Object} data
     * @param {Object} options
     * @param {string} options.default_username
     * @param {string} options.serverURL
     */
    init: function (parent, data, options) {
        this._super(...arguments);

        if (parent._isChatbot) {
            this._chatbotAvatarUrl = parent._chatbot.chatbot_avatar_url;
            this._chatbotId = parent._chatbot.chatbot_script_id;
            this._chatbotName = parent._chatbot.chatbot_name;
            this._chatbotOperatorPartnerId = parent._chatbot.chatbot_operator_partner_id;

            this._chatbotStepId = data.chatbot_script_step_id;
            this._chatbotStepAnswers = data.chatbot_step_answers;
            this._chatbotStepAnswerId = data.chatbot_selected_answer_id;
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Small override to return a placeholder in case there is no image configured on the chatbot.
     */
    getAvatarSource: function () {
        if (this._chatbotAvatarUrl && this.getAuthorID() === this._chatbotOperatorPartnerId) {
            return this._chatbotAvatarUrl;
        } else {
            return this._super(...arguments);
        }
    },

    /**
     * Get chat bot script step ID
     *
     * @return {string}
     */
    getChatbotStepId: function () {
        return this._chatbotStepId;
    },
    /**
     * Get chat bot script answers
     *
     * @return {string}
     */
    getChatbotStepAnswers: function () {
        return this._chatbotStepAnswers;
    },
    /**
     * Get chat bot script answer ID
     *
     * @return {string}
     */
    getChatbotStepAnswerId: function () {
        return this._chatbotStepAnswerId;
    },
    /**
     * @override
     */
    setChatbotStepAnswerId: function (chatbotStepAnswerId) {
        this._chatbotStepAnswerId = chatbotStepAnswerId;
    }
});

export default WebsiteLivechatMessage;
