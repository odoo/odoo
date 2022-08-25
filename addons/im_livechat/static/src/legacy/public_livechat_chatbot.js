/** @odoo-module **/

import core from 'web.core';
import session from 'web.session';
import time from 'web.time';
import utils from 'web.utils';

import LivechatButton from '@im_livechat/legacy/widgets/livechat_button';

const _t = core._t;

/**
 * Override of the LivechatButton to include chatbot capabilities.
 * Main changes / hooking points are:
 * - Show a custom welcome message that is in fact the first message of the chatbot script
 * - When messages are rendered, add click handles to chatbot options
 * - When the user picks an option or answers to the chatbot, display a "chatbot is typing..."
 *   message for a couple seconds and then trigger the next step of the script
 */
 LivechatButton.include({

    //--------------------------------------------------------------------------
    // Private - Chatbot specifics
    //--------------------------------------------------------------------------

    /**
     * A special case is handled for email steps, where we first validate the email (server side)
     * and we allow the user to try again in case the format is incorrect.
     *
     * The validation is made server-side to have the same test when we validate here and when we
     * register the answer, but also to easily post a message as the bot ("Sorry, try again...").
     *
     * Returns a boolean stating whether the email was valid or not.
     *
     * @private
     */
    async _chatbotValidateEmail() {
        let emailValidResult = await session.rpc('/chatbot/step/validate_email', {
            channel_uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid,
        });

        if (emailValidResult.success) {
            this.messaging.publicLivechatGlobal.chatbot.currentStep.data.is_email_valid = true;
            this.messaging.publicLivechatGlobal.chatbot.saveSession();

            return true;
        } else {
            // email is not valid, let the user try again
            this.messaging.publicLivechatGlobal.chatWindow.enableInput();
            if (emailValidResult.posted_message) {
                this.messaging.publicLivechatGlobal.chatbot.addMessage(emailValidResult.posted_message);
            }

            return false;
        }
    },

     //--------------------------------------------------------------------------
     // Private - LiveChat Overrides
     //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _prepareGetSessionParameters() {
        const parameters = this._super(...arguments);

        if (this.messaging.publicLivechatGlobal.livechatButtonView.isChatbot) {
            parameters.chatbot_script_id = this.messaging.publicLivechatGlobal.chatbot.scriptId;
        }

        return parameters;
    },
    /**
     * @private
     */
    _renderMessages() {
        this._super(...arguments);

        const self = this;

        this.messaging.publicLivechatGlobal.chatWindow.widget.$('.o_thread_message:last .o_livechat_chatbot_options li').each(function () {
            $(this).on('click', self._onChatbotOptionClicked.bind(self));
        });

        this.messaging.publicLivechatGlobal.chatWindow.widget.$('.o_livechat_chatbot_main_restart').on('click',
            this.messaging.publicLivechatGlobal.livechatButtonView.onChatbotRestartScript
        );

        if (this.messaging.publicLivechatGlobal.messages.length !== 0) {
            const lastMessage = this.messaging.publicLivechatGlobal.lastMessage;
            const stepAnswers = lastMessage.widget.getChatbotStepAnswers();
            if (stepAnswers && stepAnswers.length !== 0 && !lastMessage.widget.getChatbotStepAnswerId()) {
                this.messaging.publicLivechatGlobal.chatWindow.disableInput(_t('Select an option above'));
            }
        }
    },
    /**
     * Small override to handle chatbot welcome message(s).
     * @private
     */
    _sendWelcomeMessage() {
        if (this.messaging.publicLivechatGlobal.livechatButtonView.isChatbot) {
            this._sendWelcomeChatbotMessage(
                0,
                this.messaging.publicLivechatGlobal.chatbot.state === 'welcome' ? 0 : this.messaging.publicLivechatGlobal.chatbot.messageDelay,
            );
        } else {
            this._super(...arguments);
        }
    },
    /**
     * The bot can say multiple messages in quick succession as "welcome messages".
     * (See chatbot.script#_get_welcome_steps() for more details).
     *
     * It is important that those messages are sent as "welcome messages", meaning manually added
     * within the template, without creating actual mail.messages in the mail.channel.
     *
     * Indeed, if the end-user never interacts with the bot, those empty mail.channels are deleted
     * by a garbage collector mechanism.
     *
     * About "welcomeMessageDelay":
     *
     * The first time we open the chat, we want to bot to slowly input those messages in one at a
     * time, with pauses during which the end-user sees ("The bot is typing...").
     *
     * However, if the user navigates within the website (meaning he has an opened mail.channel),
     * then we input all the welcome messages at once without pauses, to avoid having that annoying
     * slow effect on every page / refresh.
     *
     * @private
     */
    _sendWelcomeChatbotMessage(stepIndex, welcomeMessageDelay) {
        const chatbotStep = this.messaging.publicLivechatGlobal.chatbot.welcomeSteps[stepIndex];
        this.messaging.publicLivechatGlobal.chatbot.update({ currentStep: { data: chatbotStep } });

        if (chatbotStep.chatbot_step_message) {
            this.messaging.publicLivechatGlobal.livechatButtonView.addMessage({
                id: '_welcome_' + stepIndex,
                is_discussion: true, // important for css style -> we only want white background for chatbot
                author_id: (
                    this.messaging.publicLivechatGlobal.publicLivechat.operator
                    ? [
                        this.messaging.publicLivechatGlobal.publicLivechat.operator.id,
                        this.messaging.publicLivechatGlobal.publicLivechat.operator.name,
                    ]
                    : []
                ),
                body: utils.Markup(chatbotStep.chatbot_step_message),
                chatbot_script_step_id: chatbotStep.chatbot_script_step_id,
                chatbot_step_answers: chatbotStep.chatbot_step_answers,
                date: time.datetime_to_str(new Date()),
                model: "mail.channel",
                message_type: "comment",
                res_id: this.messaging.publicLivechatGlobal.publicLivechat.id,
            });
        }

        if (stepIndex + 1 < this.messaging.publicLivechatGlobal.chatbot.welcomeSteps.length) {
            if (welcomeMessageDelay !== 0) {
                this.messaging.publicLivechatGlobal.chatbot.setIsTyping(true);
            }

            this.messaging.publicLivechatGlobal.chatbot.update({
                welcomeMessageTimeout: setTimeout(() => {
                    this._sendWelcomeChatbotMessage(stepIndex + 1, welcomeMessageDelay);
                    this._renderMessages();
                }, welcomeMessageDelay),
            });
        } else {
            if (this.messaging.publicLivechatGlobal.chatbot.currentStep.data.chatbot_step_type === 'forward_operator') {
                // special case when the last welcome message is a forward to an operator
                // we need to save the welcome messages before continuing the script
                // indeed, if there are no operator available, the script will continue
                // with steps that are NOT included in the welcome messages
                // (hence why we need to have those welcome messages posted BEFORE that)
                this.messaging.publicLivechatGlobal.chatbot.postWelcomeMessages();
            }

            // we are done posting welcome messages, let's start the actual script
            this.messaging.publicLivechatGlobal.chatbot.processStep();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Saves the selected chatbot.script.answer onto our chatbot.message.
     * Will update the state of the related message (in this.messaging.publicLivechatGlobal.messages) to set the selected option
     * as well which will in turn adapt the display to not show options anymore.
     *
     * This method also handles an optional redirection link placed on the chatbot.script.answer and
     * will make sure to properly save the selected choice before redirecting.
     *
     * @param {MouseEvent} ev
     * @private
     */
    async _onChatbotOptionClicked(ev) {
        ev.stopPropagation();

        const $target = $(ev.currentTarget);
        const stepId = $target.closest('ul').data('chatbotStepId');
        const selectedAnswer = $target.data('chatbotStepAnswerId');

        const redirectLink = $target.data('chatbotStepRedirectLink');
        this.messaging.publicLivechatGlobal.chatbot.update({ isRedirecting: !!redirectLink });

        await this.messaging.publicLivechatGlobal.livechatButtonView.sendMessage({
            content: $target.text().trim(),
        });

        let stepMessage = null;
        for (const message of this.messaging.publicLivechatGlobal.messages) {
            // we do NOT want to use a 'find' here because we want the LAST message that respects
            // this condition.
            // indeed, if you restart the script, you can have multiple messages with the same step id,
            // but here we only care about the very last one (the current step of the script)
            // reversing the this.messages variable seems like a bad idea because it could have
            // bad implications for other flows (as the reverse is in-place, not in a copy)
            if (message.widget.getChatbotStepId() === stepId) {
                stepMessage = message;
            }
        }
        const messageId = stepMessage.id;
        stepMessage.widget.setChatbotStepAnswerId(selectedAnswer);
        this.messaging.publicLivechatGlobal.chatbot.currentStep.data.chatbot_selected_answer_id = selectedAnswer;
        this._renderMessages();
        this.messaging.publicLivechatGlobal.chatbot.saveSession();

        const saveAnswerPromise = session.rpc('/chatbot/answer/save', {
            channel_uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid,
            message_id: messageId,
            selected_answer_id: selectedAnswer,
        });

        if (redirectLink) {
            await saveAnswerPromise;  // ensure answer is saved before redirecting
            window.location = redirectLink;
        }
    },
});

export default LivechatButton;
