/** @odoo-module **/

import core from 'web.core';
import session from 'web.session';
import time from 'web.time';
import utils from 'web.utils';

import LivechatButton from '@im_livechat/legacy/widgets/livechat_button';
import { increment } from '@mail/model/model_field_command';

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
     * Add message posted by the bot into the conversation.
     * This allows not having to wait for the bus (since we run checks based on messages in the
     * conversation, having the result be there immediately eases the process).
     *
     * It also helps while running test tours since those don't have the bus enabled.
     */
    _chatbotAddMessage(message, options) {
        message.body = utils.Markup(message.body);
        this.messaging.publicLivechatGlobal.livechatButtonView.addMessage(message, options);
        if (this.messaging.publicLivechatGlobal.publicLivechat.isFolded || !this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.isAtBottom()) {
            this.messaging.publicLivechatGlobal.publicLivechat.update({ unreadCounter: increment() });
        }

        if (!options || !options.skipRenderMessages) {
            this._renderMessages();
        }
    },

    /**
     * When the user first interacts with the bot, we want to make sure to actually post the welcome
     * messages into the conversation.
     *
     * Indeed, before that, they are 'virtual' messages that are not tied to mail.messages, see
     * #_sendWelcomeChatbotMessage() for more information.
     *
     * Posting them as real messages allows to have a cleaner model and conversation, that will be
     * kept intact when changing page on the website.
     *
     * It also allows tying any first response / question_selection choice to a chatbot.message
     * that has a linked mail.message.
     */
    async _chatbotPostWelcomeMessages() {
        const welcomeMessages = this._getWelcomeMessages();

        if (welcomeMessages.length === 0) {
            // we already posted the welcome messages, nothing to do
            return;
        }

        const postedWelcomeMessages = await session.rpc('/chatbot/post_welcome_steps', {
            channel_uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid,
            chatbot_script_id: this.messaging.publicLivechatGlobal.chatbot.scriptId,
        });

        const welcomeMessagesIds = welcomeMessages.map(welcomeMessage => welcomeMessage.id);
        this.messaging.publicLivechatGlobal.update({
            messages: this.messaging.publicLivechatGlobal.messages.filter((message) => {
                !welcomeMessagesIds.includes(message.id);
            }),
        });

        postedWelcomeMessages.reverse();
        postedWelcomeMessages.forEach((message) => {
            this._chatbotAddMessage(message, {
                prepend: true,
                skipRenderMessages: true,
            });
        });

        this._renderMessages();
    },

    /**
     * Disable the input allowing the user to type.
     * This is typically used when we want to force him to click on one of the chatbot options.
     *
     * @private
     */
    _chatbotDisableInput(disableText) {
        this.messaging.publicLivechatGlobal.chatWindow.legacyChatWindow.$('.o_composer_text_field')
            .prop('disabled', true)
            .addClass('text-center fst-italic bg-200')
            .val(disableText);
    },

    /**
     * @private
     */
    _chatbotEnableInput() {
        const $composerTextField = this.messaging.publicLivechatGlobal.chatWindow.legacyChatWindow.$('.o_composer_text_field');
        $composerTextField
            .prop('disabled', false)
            .removeClass('text-center fst-italic bg-200')
            .val('')
            .focus();

        if (this.chatbotInputKeyDownHandler) {
            $composerTextField.off('keydown', this.chatbotInputKeyDownHandler);
        }

        if (this.messaging.publicLivechatGlobal.chatbot.currentStep.data.chatbot_step_type === 'free_input_multi') {
            this.chatbotInputKeyDownHandler = this._onChatbotInputKeyDown.bind(this);
            $composerTextField.on('keydown', this.chatbotInputKeyDownHandler);
        }
    },
    /**
     * Processes the step, depending on the current state of the script and the author of the last
     * message that was typed into the conversation.
     *
     * This is a rather complicated process since we have many potential states to handle.
     * Here are the detailed possible outcomes:
     *
     * - Check if the script is finished, and if so end it.
     *
     * - If a human operator has taken over the conversation
     *   -> enable the input and let the operator handle the visitor.
     *
     * - If the received step is of type expecting an input from the user
     *   - the last message if from the user (he has already answered)
     *     -> trigger the next step
     *   - otherwise
     *     -> enable the input and let the user type
     *
     * - Otherwise
     *   - if the the step is of type 'question_selection' and we are still waiting for the user to
     *     select one of the options
     *     -> don't do anything, wait for the user to click one of the options
     *   - otherwise
     *     -> trigger the next step
     *
     * @private
     */
    _chatbotProcessStep() {
        if (this.messaging.publicLivechatGlobal.chatbot.shouldEndScript) {
            this.messaging.publicLivechatGlobal.chatbot.endScript();
        } else if (this.messaging.publicLivechatGlobal.chatbot.currentStep.data.chatbot_step_type === 'forward_operator'
                   && this.messaging.publicLivechatGlobal.chatbot.currentStep.data.chatbot_operator_found) {
            this._chatbotEnableInput();
        }  else if (this.messaging.publicLivechatGlobal.chatbot.isExpectingUserInput) {
            if (this.messaging.publicLivechatGlobal.isLastMessageFromCustomer) {
                // user has already typed a message in -> trigger next step
                this.messaging.publicLivechatGlobal.chatbot.setIsTyping();
                this.messaging.publicLivechatGlobal.chatbot.update({
                    nextStepTimeout: setTimeout(
                        this.messaging.publicLivechatGlobal.chatbot.triggerNextStep,
                        this.messaging.publicLivechatGlobal.chatbot.messageDelay,
                    ),
                });
            } else {
                this._chatbotEnableInput();
            }
        } else {
            let triggerNextStep = true;
            if (this.messaging.publicLivechatGlobal.chatbot.currentStep.data.chatbot_step_type === 'question_selection') {
                if (!this.messaging.publicLivechatGlobal.isLastMessageFromCustomer) {
                    // if there is no last message or if the last message is from the bot
                    // -> don't trigger the next step, we are waiting for the user to pick an option
                    triggerNextStep = false;
                }
            }

            if (triggerNextStep) {
                let nextStepDelay = this.messaging.publicLivechatGlobal.chatbot.messageDelay;
                if (this.messaging.publicLivechatGlobal.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_typing').length !== 0) {
                    // special case where we already have a "is typing" message displayed
                    // can happen when the previous step did not trigger any message posted from the bot
                    // e.g: previous step was "forward_operator" and no-one is available
                    // -> in that case, don't wait and trigger the next step immediately
                    nextStepDelay = 0;
                } else {
                    this.messaging.publicLivechatGlobal.chatbot.setIsTyping();
                }

                this.messaging.publicLivechatGlobal.chatbot.update({
                    nextStepTimeout: setTimeout(
                        this.messaging.publicLivechatGlobal.chatbot.triggerNextStep,
                        nextStepDelay,
                    ),
                });
            }
        }

        if (!this.messaging.publicLivechatGlobal.chatbot.hasRestartButton) {
            this.messaging.publicLivechatGlobal.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_main_restart').addClass('d-none');
        }
     },
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
            this._chatbotEnableInput();
            if (emailValidResult.posted_message) {
                this._chatbotAddMessage(emailValidResult.posted_message);
            }

            return false;
        }
    },
    /**
     * Returns the 'this.messaging.publicLivechatGlobal.messages' filtered on our special 'welcome' ones.
     * See '_sendWelcomeChatbotMessage'.
     *
     * @private
     */
    _getWelcomeMessages() {
        return this.messaging.publicLivechatGlobal.messages.filter((message) => {
            return message.id && typeof message.id === 'string' && message.id.startsWith('_welcome_');
        });
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

        this.messaging.publicLivechatGlobal.chatWindow.legacyChatWindow.$('.o_thread_message:last .o_livechat_chatbot_options li').each(function () {
            $(this).on('click', self._onChatbotOptionClicked.bind(self));
        });

        this.messaging.publicLivechatGlobal.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_main_restart').on('click',
            this.messaging.publicLivechatGlobal.livechatButtonView.onChatbotRestartScript
        );

        if (this.messaging.publicLivechatGlobal.messages.length !== 0) {
            const lastMessage = this.messaging.publicLivechatGlobal.lastMessage;
            const stepAnswers = lastMessage.legacyPublicLivechatMessage.getChatbotStepAnswers();
            if (stepAnswers && stepAnswers.length !== 0 && !lastMessage.legacyPublicLivechatMessage.getChatbotStepAnswerId()) {
                this._chatbotDisableInput(_t('Select an option above'));
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
                this._chatbotPostWelcomeMessages();
            }

            // we are done posting welcome messages, let's start the actual script
            this._chatbotProcessStep();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onChatbotInputKeyDown() {
        if (
            this.messaging.publicLivechatGlobal.chatbot.currentStep &&
            this.messaging.publicLivechatGlobal.chatbot.currentStep.data &&
            this.messaging.publicLivechatGlobal.chatbot.currentStep.data.chatbot_step_type === 'free_input_multi'
        ) {
            this.messaging.publicLivechatGlobal.chatbot.debouncedAwaitUserInput();
        }
    },

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
            if (message.legacyPublicLivechatMessage.getChatbotStepId() === stepId) {
                stepMessage = message;
            }
        }
        const messageId = stepMessage.id;
        stepMessage.legacyPublicLivechatMessage.setChatbotStepAnswerId(selectedAnswer);
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
