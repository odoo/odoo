/** @odoo-module **/

import core from 'web.core';
import localStorage from 'web.local_storage';
import session from 'web.session';
import time from 'web.time';
import utils from 'web.utils';

import LivechatButton from '@im_livechat/legacy/widgets/livechat_button';
import { clear, increment, insertAndReplace, replace } from '@mail/model/model_field_command';

const _t = core._t;
const QWeb = core.qweb;

/**
 * Override of the LivechatButton to include chatbot capabilities.
 * Main changes / hooking points are:
 * - Show a custom welcome message that is in fact the first message of the chatbot script
 * - When messages are rendered, add click handles to chatbot options
 * - When the user picks an option or answers to the chatbot, display a "chatbot is typing..."
 *   message for a couple seconds and then trigger the next step of the script
 */
 LivechatButton.include({
    init() {
        this._super(...arguments);

        // debounced to let the user type several sentences, see '_chatbotAwaitUserInput' for details
        this._debouncedChatbotAwaitUserInput = _.debounce(
            this._chatbotAwaitUserInput.bind(this),
            10000);
    },

    /**
     * This override handles the following use cases:
     *
     * - If the chat is started for the first time (first visit of a visitor)
     *   We register the chatbot configuration and the rest of the behavior is triggered by various
     *   method overrides ('sendWelcomeMessage', 'sendMessage', ...)
     *
     * - If the chat has been started before, but the user did not interact with the bot
     *   The default behavior is to open an empty chat window, without any messages.
     *   In addition, we fetch the configuration (with a '/init' call), to see if we have a bot
     *   configured.
     *   Indeed we want to trigger the bot script on every page where the associated rule is matched.
     *
     * - If we have a non-empty chat history, resume the chat script where the end-user left it by
     *   fetching the necessary information from the local storage.
     *
     * @override
     */
    async willStart() {
        const superResult = await this._super(...arguments);

        if (this.messaging.publicLivechatGlobal.livechatButtonView.rule && !!this.messaging.publicLivechatGlobal.livechatButtonView.rule.chatbot) {
            // noop
        } else if (this.messaging.publicLivechatGlobal.livechatButtonView.history !== null && this.messaging.publicLivechatGlobal.livechatButtonView.history.length === 0) {
            this.messaging.publicLivechatGlobal.livechatButtonView.update({ livechatInit: await session.rpc('/im_livechat/init', {channel_id: this.messaging.publicLivechatGlobal.livechatButtonView.channelId}) });
        } else if (this.messaging.publicLivechatGlobal.livechatButtonView.history !== null && this.messaging.publicLivechatGlobal.livechatButtonView.history.length !== 0) {
            const sessionCookie = utils.get_cookie('im_livechat_session');
            if (sessionCookie) {
                this.messaging.publicLivechatGlobal.livechatButtonView.update({ sessionCookie });
                if (localStorage.getItem(this.messaging.publicLivechatGlobal.livechatButtonView.chatbotSessionCookieKey)) {
                    this.messaging.publicLivechatGlobal.livechatButtonView.update({ chatbotState: 'restore_session' });
                }
            }
        }

        if (this.messaging.publicLivechatGlobal.livechatButtonView.chatbotState === 'init') {
            // we landed on a website page where a channel rule is configured to run a chatbot.script
            // -> initialize necessary state
            if (this.messaging.publicLivechatGlobal.livechatButtonView.rule.chatbot_welcome_steps && this.messaging.publicLivechatGlobal.livechatButtonView.rule.chatbot_welcome_steps.length !== 0) {
                this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.update({
                    currentStep: insertAndReplace({
                        data: this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.lastWelcomeStep,
                    }),
                });
            }
        } else if (this.messaging.publicLivechatGlobal.livechatButtonView.chatbotState === 'welcome') {
            // we landed on a website page and a chatbot script was initialized on a previous one
            // however the end-user did not interact with the bot ( :( )
            // -> remove cookie to force opening the popup again
            // -> initialize necessary state
            // -> batch welcome message (see '_sendWelcomeChatbotMessage')
            utils.set_cookie('im_livechat_auto_popup', '', -1);
            this.messaging.publicLivechatGlobal.livechatButtonView.update({ history: clear() });
            this.messaging.publicLivechatGlobal.livechatButtonView.update({ rule: this.messaging.publicLivechatGlobal.livechatButtonView.livechatInit.rule });
        } else if (this.messaging.publicLivechatGlobal.livechatButtonView.chatbotState === 'restore_session') {
            // we landed on a website page and a chatbot script is currently running
            // -> restore the user's session (see 'chatbotRestoreSession')
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbotRestoreSession();
        }

        return superResult;
    },

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
        if (this.messaging.publicLivechatGlobal.publicLivechat.isFolded || !this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow._publicLivechatView.isAtBottom()) {
            this.messaging.publicLivechatGlobal.publicLivechat.update({ unreadCounter: increment() });
        }

        if (!options || !options.skipRenderMessages) {
            this._renderMessages();
        }
    },

    /**
     * This method will be transformed into a 'debounced' version (see init).
     *
     * The purpose is to handle steps of type 'free_input_multi', that will let the user type in
     * multiple lines of text before the bot goes to the next step.
     *
     * Every time a 'keydown' is detected into the input, or every time a message is sent, we call
     * this debounced method, which will give the user about 10 seconds to type more text before
     * the next step is triggered.
     *
     * First we check if the last message was sent by the user, to make sure we always let him type
     * at least one message before moving on.
     */
    _chatbotAwaitUserInput() {
        if (this._isLastMessageFromCustomer()) {
            if (this._chatbotShouldEndScript()) {
                this._chatbotEndScript();
            } else {
                this._chatbotSetIsTyping();
                this.messaging.publicLivechatGlobal.livechatButtonView.update({
                    chatbotNextStepTimeout: setTimeout(
                        this._chatbotTriggerNextStep.bind(this),
                        this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.messageDelay,
                    )
                });
            }
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
            chatbot_script_id: this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.scriptId,
        });

        const welcomeMessagesIds = welcomeMessages.map(welcomeMessage => welcomeMessage.id);
        this.messaging.publicLivechatGlobal.livechatButtonView.update({
            messages: replace(
                this.messaging.publicLivechatGlobal.livechatButtonView.messages.filter((message) => {
                    !welcomeMessagesIds.includes(message.id);
                }),
            ),
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
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_composer_text_field')
            .prop('disabled', true)
            .addClass('text-center fst-italic bg-200')
            .val(disableText);
    },

    /**
     * @private
     */
    _chatbotEnableInput() {
        const $composerTextField = this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_composer_text_field');
        $composerTextField
            .prop('disabled', false)
            .removeClass('text-center fst-italic bg-200')
            .val('')
            .focus();

        if (this.chatbotInputKeyDownHandler) {
            $composerTextField.off('keydown', this.chatbotInputKeyDownHandler);
        }

        if (this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_type === 'free_input_multi') {
            this.chatbotInputKeyDownHandler = this._onChatbotInputKeyDown.bind(this);
            $composerTextField.on('keydown', this.chatbotInputKeyDownHandler);
        }
    },
    /**
     * Once the script ends, adds a visual element at the end of the chat window allowing to restart
     * the whole script.
     *
     * @private
     */
    _chatbotEndScript() {
        if (
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep &&
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data &&
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.conversation_closed
        ) {
            // don't touch anything if the user has closed the conversation, let the chat window
            // handle the display
            return;
        }
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_composer_text_field').addClass('d-none');
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_end').show();
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_restart').one('click',
            this._onChatbotRestartScript.bind(this));

    },
    /**
     * Will display a "Restart script" button in the conversation toolbar.
     *
     * Side-case: if the conversation has been forwarded to a human operator, we don't want to
     * display that restart button.
     *
     * @private
     */
    _chatbotDisplayRestartButton() {
        return this.messaging.publicLivechatGlobal.livechatButtonView.isChatbot && (!this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep ||
            (this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_type !== 'forward_operator' ||
             !this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_operator_found));
    },
    /**
     * Works as a hook since other modules can add their own step types.
     *
     * @private
     */
    _chatbotIsExpectingUserInput() {
        return [
            'question_phone',
            'question_email',
            'free_input_single',
            'free_input_multi',
        ].includes(this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_type);
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
        if (this._chatbotShouldEndScript()) {
            this._chatbotEndScript();
        } else if (this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_type === 'forward_operator'
                   && this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_operator_found) {
            this._chatbotEnableInput();
        }  else if (this._chatbotIsExpectingUserInput()) {
            if (this._isLastMessageFromCustomer()) {
                // user has already typed a message in -> trigger next step
                this._chatbotSetIsTyping();
                this.messaging.publicLivechatGlobal.livechatButtonView.update({
                    chatbotNextStepTimeout: setTimeout(
                        this._chatbotTriggerNextStep.bind(this),
                        this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.messageDelay,
                    ),
                });
            } else {
                this._chatbotEnableInput();
            }
        } else {
            let triggerNextStep = true;
            if (this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_type === 'question_selection') {
                if (!this._isLastMessageFromCustomer()) {
                    // if there is no last message or if the last message is from the bot
                    // -> don't trigger the next step, we are waiting for the user to pick an option
                    triggerNextStep = false;
                }
            }

            if (triggerNextStep) {
                let nextStepDelay = this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.messageDelay;
                if (this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_typing').length !== 0) {
                    // special case where we already have a "is typing" message displayed
                    // can happen when the previous step did not trigger any message posted from the bot
                    // e.g: previous step was "forward_operator" and no-one is available
                    // -> in that case, don't wait and trigger the next step immediately
                    nextStepDelay = 0;
                } else {
                    this._chatbotSetIsTyping();
                }

                this.messaging.publicLivechatGlobal.livechatButtonView.update({
                    chatbotNextStepTimeout: setTimeout(
                        this._chatbotTriggerNextStep.bind(this),
                        nextStepDelay,
                    ),
                });
            }
        }

        if (!this._chatbotDisplayRestartButton()) {
            this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_main_restart').addClass('d-none');
        }
     },
    /**
     * Register current chatbot step state into localStorage to be able to resume if the visitor
     * goes to another website page or if he refreshes his page.
     *
     * (Will not work if the visitor switches browser but his livechat session will not be restored
     *  anyway in that case, since it's stored into a cookie).
     *
     * @private
     */
    _chatbotSaveSession() {
        localStorage.setItem('im_livechat.chatbot.state.uuid_' + this.messaging.publicLivechatGlobal.publicLivechat.uuid, JSON.stringify({
            '_chatbot': this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.data,
            '_chatbotCurrentStep': this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data,
        }));
    },
    /**
     * Adds a small "is typing" animation into the chat window.
     *
     * @private
     */
    _chatbotSetIsTyping(isWelcomeMessage=false) {
        if (this.messaging.publicLivechatGlobal.livechatButtonView.isTypingTimeout) {
            clearTimeout(this.isTypingTimeout);
        }

        this._chatbotDisableInput('');

        this.messaging.publicLivechatGlobal.livechatButtonView.update({
            isTypingTimeout: setTimeout(() => {
                this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_mail_thread_content').append(
                    $(QWeb.render('im_livechat.legacy.chatbot.is_typing_message', {
                        'chatbotImageSrc': `/im_livechat/operator/${
                            this.messaging.publicLivechatGlobal.publicLivechat.operator.id
                        }/avatar`,
                        'chatbotName': this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.name,
                        'isWelcomeMessage': isWelcomeMessage,
                    }))
                );

                this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow._publicLivechatView.scrollToBottom();
            }, this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.messageDelay / 3),
        });
    },
    /**
     * Helper method that checks if the script should be ended or not.
     * If the user has closed the conversation -> script has ended.
     *
     * Otherwise, there are 2 use cases where we want to end the script:
     *
     * If the current step is the last one AND the conversation was not taken over by a human operator
     *   1. AND we expect a user input (or we are on a selection)
     *       AND the user has already answered
     *   2. AND we don't expect a user input
     *
     * @returns {Boolean}
     * @private
     */
    _chatbotShouldEndScript() {
        if (this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.conversation_closed) {
            return true;
        }
        if (this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_is_last &&
            (this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_type !== 'forward_operator' ||
             !this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_operator_found)
        ) {
            if (this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_type === 'question_email'
                && !this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.is_email_valid
            ) {
                // email is not (yet) valid, let the user answer / try again
                return false;
            } else if (
                (this._chatbotIsExpectingUserInput() ||
                this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_type === 'question_selection') &&
                this.messaging.publicLivechatGlobal.livechatButtonView.messages.length !== 0
            ) {
                const lastMessage = this.messaging.publicLivechatGlobal.livechatButtonView.messages[this.messaging.publicLivechatGlobal.livechatButtonView.messages.length - 1];
                if (lastMessage.legacyPublicLivechatMessage.getAuthorID() !== this.messaging.publicLivechatGlobal.publicLivechat.operator.id) {
                    // we are on the last step of the script, expect a user input and the user has
                    // already answered
                    // -> end the script
                    return true;
                }
            } else if (!this._chatbotIsExpectingUserInput()) {
                // we are on the last step of the script and we do not expect a user input
                // -> end the script
                return true;
            }
        }

        return false;
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
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.is_email_valid = true;
            this._chatbotSaveSession();

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
     * Triggers the next step of the script by calling the associated route.
     * This will receive the next step and call step processing.
     *
     * @private
     */
    async _chatbotTriggerNextStep() {
        let triggerNextStep = true;
        if (
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep &&
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data &&
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_type === 'question_email'
        ) {
            triggerNextStep = await this._chatbotValidateEmail();
        }

        if (!triggerNextStep) {
            return;
        }

        const nextStep = await session.rpc('/chatbot/step/trigger', {
            channel_uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid,
            chatbot_script_id: this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.scriptId,
        });

        if (nextStep) {
            if (nextStep.chatbot_posted_message) {
                this._chatbotAddMessage(nextStep.chatbot_posted_message);
            }

            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.update({ currentStep: insertAndReplace({ data: nextStep.chatbot_step }) });

            this._chatbotProcessStep();
        } else {
            // did not find next step -> end the script
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_is_last = true;
            this._renderMessages();
            this._chatbotEndScript();
        }

        this._chatbotSaveSession();

        return nextStep;
    },
    /**
     * Returns the 'this.messaging.publicLivechatGlobal.livechatButtonView.messages' filtered on our special 'welcome' ones.
     * See '_sendWelcomeChatbotMessage'.
     *
     * @private
     */
    _getWelcomeMessages() {
        return this.messaging.publicLivechatGlobal.livechatButtonView.messages.filter((message) => {
            return message.id && typeof message.id === 'string' && message.id.startsWith('_welcome_');
        });
    },
    /**
     * Compares the last message of the conversation to this livechat's operator id.
     *
     * @private
     */
    _isLastMessageFromCustomer() {
        const lastMessage = this.messaging.publicLivechatGlobal.livechatButtonView.messages.length !== 0 ? this.messaging.publicLivechatGlobal.livechatButtonView.messages[this.messaging.publicLivechatGlobal.livechatButtonView.messages.length - 1] : null;
        return lastMessage && lastMessage.legacyPublicLivechatMessage.getAuthorID() !== this.messaging.publicLivechatGlobal.publicLivechat.operator.id;
    },

     //--------------------------------------------------------------------------
     // Private - LiveChat Overrides
     //--------------------------------------------------------------------------

    /**
     * When we enter the "ask feedback" process of the chat, we hide some elements that become
     * unnecessary and irrelevant (restart / end messages, any text field values, ...).
     *
     * @override
     * @private
     */
     _askFeedback() {
        this._super(...arguments);

        if (
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot &&
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep &&
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data
        ) {
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.conversation_closed = true;
            this._chatbotSaveSession();
        }
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_main_restart').addClass('d-none');
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_end').hide();
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_composer_text_field')
            .removeClass('d-none')
            .val('');
     },
    /**
     * Resuming the chatbot script if we are currently running one.
     *
     * In addition, we register a resize event on the window object to scroll messages to bottom.
     * This is done especially for mobile (Android) where the keyboard opens upon focusing the input
     * field and shrinks the whole window size.
     * Scrolling to the bottom allows the user to see the last messages properly when that happens.
     *
     * @private
     * @override
     */
    _openChatWindow() {
        return this._super(...arguments).then(() => {
            window.addEventListener('resize', () => {
                if (this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow) {
                    this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow._publicLivechatView.scrollToBottom();
                }
            });

            if (
                this.messaging.publicLivechatGlobal.livechatButtonView.chatbot &&
                this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep &&
                this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data &&
                this.messaging.publicLivechatGlobal.livechatButtonView.messages &&
                this.messaging.publicLivechatGlobal.livechatButtonView.messages.length !== 0
            ) {
                this._chatbotProcessStep();
            }
        });
    },
    /**
     * @private
     * @override
     */
    _prepareGetSessionParameters() {
        const parameters = this._super(...arguments);

        if (this.messaging.publicLivechatGlobal.livechatButtonView.isChatbot) {
            parameters.chatbot_script_id = this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.scriptId;
        }

        return parameters;
    },
    /**
     * @private
     */
    _renderMessages() {
        this._super(...arguments);

        const self = this;

        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_thread_message:last .o_livechat_chatbot_options li').each(function () {
            $(this).on('click', self._onChatbotOptionClicked.bind(self));
        });

        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_main_restart').on('click',
            this._onChatbotRestartScript.bind(this));

        if (this.messaging.publicLivechatGlobal.livechatButtonView.messages.length !== 0) {
            const lastMessage = this.messaging.publicLivechatGlobal.livechatButtonView.messages[this.messaging.publicLivechatGlobal.livechatButtonView.messages.length - 1];
            const stepAnswers = lastMessage.legacyPublicLivechatMessage.getChatbotStepAnswers();
            if (stepAnswers && stepAnswers.length !== 0 && !lastMessage.legacyPublicLivechatMessage.getChatbotStepAnswerId()) {
                this._chatbotDisableInput(_t('Select an option above'));
            }
        }
    },
    /**
     * When the Customer sends a message, we need to act depending on our current state:
     * - If the conversation has been forwarded to an operator
     *   Then there is nothing to do, we let them speak
     * - If we are currently on a 'free_input_multi' step
     *   Await more user input (see #_chatbotAwaitUserInput() for details)
     * - Otherwise we continue the script or end it if it's the last step
     *
     * We also save the current session state.
     * Important as this may be the very first interaction with the bot, we need to save right away
     * to correctly handle any page redirection / page refresh.
     *
     * Special side case: if we are currently redirecting to another page (see '_onChatbotOptionClicked')
     * we shortcut the process as we are currently moving to a different URL.
     * The script will be resumed on the new page (if in the same website domain).
     *
     * @private
     */
    async _sendMessage(message) {
        const superArguments = arguments;
        const superMethod = this._super;

        if (
            this.messaging.publicLivechatGlobal.livechatButtonView.isChatbot &&
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep &&
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data
        ) {
            await this._chatbotPostWelcomeMessages();
        }

        return superMethod.apply(this, superArguments).then(() => {
            if (this.messaging.publicLivechatGlobal.livechatButtonView.isChatbotRedirecting) {
                return;
            }

            if (
                this.messaging.publicLivechatGlobal.livechatButtonView.isChatbot &&
                this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep &&
                this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data
            ) {
                if (
                    this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_type === 'forward_operator' &&
                    this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_operator_found
                ) {
                    return;  // operator has taken over the conversation, let them speak
                } else if (this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_type === 'free_input_multi') {
                    this._debouncedChatbotAwaitUserInput();
                } else if (!this._chatbotShouldEndScript()) {
                    this._chatbotSetIsTyping();
                    this.messaging.publicLivechatGlobal.livechatButtonView.update({
                        chatbotNextStepTimeout: setTimeout(
                            this._chatbotTriggerNextStep.bind(this),
                            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.messageDelay,
                        ),
                    });
                } else {
                    this._chatbotEndScript();
                }

                this._chatbotSaveSession();
            }
        });
    },
    /**
     * Small override to handle chatbot welcome message(s).
     * @private
     */
    _sendWelcomeMessage() {
        if (this.messaging.publicLivechatGlobal.livechatButtonView.isChatbot) {
            this._sendWelcomeChatbotMessage(
                0,
                this.messaging.publicLivechatGlobal.livechatButtonView.chatbotState === 'welcome' ? 0 : this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.messageDelay,
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
        const chatbotStep = this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.welcomeSteps[stepIndex];
        this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.update({ currentStep: insertAndReplace({ data: chatbotStep }) });

        if (chatbotStep.chatbot_step_message) {
            this.messaging.publicLivechatGlobal.livechatButtonView.addMessage({
                id: '_welcome_' + stepIndex,
                is_discussion: true,  // important for css style -> we only want white background for chatbot
                attachment_ids: [],
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

        if (stepIndex + 1 < this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.welcomeSteps.length) {
            if (welcomeMessageDelay !== 0) {
                this._chatbotSetIsTyping(true);
            }

            this.messaging.publicLivechatGlobal.livechatButtonView.update({
                chatbotWelcomeMessageTimeout: setTimeout(() => {
                    this._sendWelcomeChatbotMessage(stepIndex + 1, welcomeMessageDelay);
                    this._renderMessages();
                }, welcomeMessageDelay),
            });
        } else {
            if (this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_type === 'forward_operator') {
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

    /**
     * Restart the script and then trigger the "next step" (which will be the first of the script
     * in this case).
     *
     * @private
     */
    async _onChatbotRestartScript(ev) {
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_composer_text_field').removeClass('d-none');
        this.messaging.publicLivechatGlobal.livechatButtonView.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_end').hide();

        if (this.messaging.publicLivechatGlobal.livechatButtonView.chatbotNextStepTimeout) {
            clearTimeout(this.messaging.publicLivechatGlobal.livechatButtonView.chatbotNextStepTimeout);
        }

        if (this.messaging.publicLivechatGlobal.livechatButtonView.chatbotWelcomeMessageTimeout) {
            clearTimeout(this.messaging.publicLivechatGlobal.livechatButtonView.chatbotWelcomeMessageTimeout);
        }

        const postedMessage = await session.rpc('/chatbot/restart', {
            channel_uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid,
            chatbot_script_id: this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.scriptId,
        });

        if (postedMessage) {
            this._chatbotAddMessage(postedMessage);
        }

        this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.update({ currentStep: clear() });
        this._chatbotSetIsTyping();
        this.messaging.publicLivechatGlobal.livechatButtonView.update({
            chatbotNextStepTimeout: setTimeout(
                this._chatbotTriggerNextStep.bind(this),
                this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.messageDelay,
            ),
        });
    },

    _onChatbotInputKeyDown() {
        if (
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep &&
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data &&
            this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_step_type === 'free_input_multi'
        ) {
            this._debouncedChatbotAwaitUserInput();
        }
    },

    /**
     * Saves the selected chatbot.script.answer onto our chatbot.message.
     * Will update the state of the related message (in this.messaging.publicLivechatGlobal.livechatButtonView.messages) to set the selected option
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
        this.messaging.publicLivechatGlobal.livechatButtonView.update({ isChatbotRedirecting: !!redirectLink });

        await this._sendMessage({
            content: $target.text().trim(),
        });

        let stepMessage = null;
        for (const message of this.messaging.publicLivechatGlobal.livechatButtonView.messages) {
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
        this.messaging.publicLivechatGlobal.livechatButtonView.chatbot.currentStep.data.chatbot_selected_answer_id = selectedAnswer;
        this._renderMessages();
        this._chatbotSaveSession();

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
