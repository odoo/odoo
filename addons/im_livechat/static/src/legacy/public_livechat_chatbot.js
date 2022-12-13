/** @odoo-module **/

import core from 'web.core';
import localStorage from 'web.local_storage';
import session from 'web.session';
import time from 'web.time';
import utils from 'web.utils';

import LivechatButton from 'im_livechat.legacy.im_livechat.im_livechat';

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
 LivechatButton.LivechatButton.include({
    init: function () {
        this._super(...arguments);

        this._chatbotMessageDelay = 3500;  // in milliseconds

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
    willStart: async function () {
        const superResult = await this._super(...arguments);

        const strCookie = utils.get_cookie('im_livechat_session');
        const isSessionCookieAvailable = Boolean(strCookie);
        const cookie = JSON.parse(strCookie|| '{}');
        if (isSessionCookieAvailable && !cookie.chatbot_script_id) {
            return;
        }

        this._isChatbot = false;
        this.chatbotState = null;

        if (this._rule && !!this._rule.chatbot) {
            this._isChatbot = true;
            this.chatbotState = 'init';
        } else if (this._history !== null && this._history.length === 0) {
            this._livechatInit = await session.rpc('/im_livechat/init', {channel_id: this.options.channel_id});

            if (this._livechatInit.rule.chatbot) {
                this._isChatbot = true;
                this.chatbotState = 'welcome';
            }
        } else if (this._history !== null && this._history.length !== 0) {
            const sessionCookie = utils.get_cookie('im_livechat_session');
            if (sessionCookie) {
                const sessionKey = 'im_livechat.chatbot.state.uuid_' + JSON.parse(sessionCookie).uuid;
                if (localStorage.getItem(sessionKey)) {
                    this._isChatbot = true;
                    this.chatbotState = 'restore_session';
                }
            }
        }

        if (this._isChatbot) {
            // void the default livechat placeholder in the user input
            // as we use it for specific things (e.g: showing "please select an option above")
            this.options.input_placeholder = '';
        }

        if (this.chatbotState === 'init') {
            // we landed on a website page where a channel rule is configured to run a chatbot.script
            // -> initialize necessary state
            this._chatbot = this._rule.chatbot;
            if (this._rule.chatbot_welcome_steps && this._rule.chatbot_welcome_steps.length !== 0) {
                this._chatbotCurrentStep = this._chatbot.chatbot_welcome_steps[
                    this._chatbot.chatbot_welcome_steps.length - 1];
            }
        } else if (this.chatbotState === 'welcome') {
            // we landed on a website page and a chatbot script was initialized on a previous one
            // however the end-user did not interact with the bot ( :( )
            // -> remove cookie to force opening the popup again
            // -> initialize necessary state
            // -> batch welcome message (see '_sendWelcomeChatbotMessage')
            utils.set_cookie('im_livechat_auto_popup', '', -1);
            this._history = null;
            this._rule = this._livechatInit.rule;
            this._chatbot = this._livechatInit.rule.chatbot;
            this._isChatbot = true;
            this._chatbotBatchWelcomeMessages = true;
        } else if (this.chatbotState === 'restore_session') {
            // we landed on a website page and a chatbot script is currently running
            // -> restore the user's session (see '_chatbotRestoreSession')
            this._chatbotRestoreSession(utils.get_cookie('im_livechat_session'));
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
    _chatbotAddMessage: function (message, options) {
        message.body = utils.Markup(message.body);
        this._addMessage(message, options);
        if (this._chatWindow.isFolded() || !this._chatWindow.isAtBottom()) {
            this._livechat.incrementUnreadCounter();
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
    _chatbotAwaitUserInput: function () {
        if (this._isLastMessageFromCustomer()) {
            if (this._chatbotShouldEndScript()) {
                this._chatbotEndScript();
            } else {
                this._chatbotSetIsTyping();
                this.nextStepTimeout = setTimeout(
                    this._chatbotTriggerNextStep.bind(this), this._chatbotMessageDelay);
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
    _chatbotPostWelcomeMessages: async function () {
        const welcomeMessages = this._getWelcomeMessages();

        if (welcomeMessages.length === 0) {
            // we already posted the welcome messages, nothing to do
            return;
        }

        const postedWelcomeMessages = await session.rpc('/chatbot/post_welcome_steps', {
            channel_uuid: this._livechat.getUUID(),
            chatbot_script_id: this._chatbot.chatbot_script_id,
        });

        const welcomeMessagesIds = welcomeMessages.map(welcomeMessage => welcomeMessage._id);
        this._messages = this._messages.filter((message) => {
            !welcomeMessagesIds.includes(message._id);
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
    _chatbotDisableInput: function (disableText) {
        this._chatWindow.$('.o_composer_text_field')
            .prop('disabled', true)
            .addClass('text-center font-italic bg-200')
            .val(disableText);
    },

    /**
     * @private
     */
    _chatbotEnableInput: function () {
        const $composerTextField = this._chatWindow.$('.o_composer_text_field');
        $composerTextField
            .prop('disabled', false)
            .removeClass('text-center font-italic bg-200')
            .val('')
            .focus();

        if (this.chatbotInputKeyDownHandler) {
            $composerTextField.off('keydown', this.chatbotInputKeyDownHandler);
        }

        if (this._chatbotCurrentStep.chatbot_step_type === 'free_input_multi') {
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
    _chatbotEndScript: function () {
        if (this._chatbotCurrentStep && this._chatbotCurrentStep.conversation_closed) {
            // don't touch anything if the user has closed the conversation, let the chat window
            // handle the display
            return;
        }

        this._chatWindow.$('.o_composer_text_field').addClass('d-none');
        this._chatWindow.$('.o_livechat_chatbot_end').show();
        this._chatWindow.$('.o_livechat_chatbot_restart').one('click',
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
    _chatbotDisplayRestartButton: function () {
        return this._isChatbot && (!this._chatbotCurrentStep ||
            (this._chatbotCurrentStep.chatbot_step_type !== 'forward_operator' ||
             !this._chatbotCurrentStep.chatbot_operator_found));
    },
    /**
     * Works as a hook since other modules can add their own step types.
     *
     * @private
     */
    _chatbotIsExpectingUserInput: function () {
        return [
            'question_phone',
            'question_email',
            'free_input_single',
            'free_input_multi',
        ].includes(this._chatbotCurrentStep.chatbot_step_type);
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
    _chatbotProcessStep: function () {
        if (this._chatbotShouldEndScript()) {
            this._chatbotEndScript();
        } else if (this._chatbotCurrentStep.chatbot_step_type === 'forward_operator'
                   && this._chatbotCurrentStep.chatbot_operator_found) {
            this._chatbotEnableInput();
        }  else if (this._chatbotIsExpectingUserInput()) {
            if (this._isLastMessageFromCustomer()) {
                // user has already typed a message in -> trigger next step
                this._chatbotSetIsTyping();
                this.nextStepTimeout = setTimeout(
                    this._chatbotTriggerNextStep.bind(this), this._chatbotMessageDelay);
            } else {
                this._chatbotEnableInput();
            }
        } else {
            let triggerNextStep = true;
            if (this._chatbotCurrentStep.chatbot_step_type === 'question_selection') {
                if (!this._isLastMessageFromCustomer()) {
                    // if there is no last message or if the last message is from the bot
                    // -> don't trigger the next step, we are waiting for the user to pick an option
                    triggerNextStep = false;
                }
            }

            if (triggerNextStep) {
                let nextStepDelay = this._chatbotMessageDelay;
                if (this._chatWindow.$('.o_livechat_chatbot_typing').length !== 0) {
                    // special case where we already have a "is typing" message displayed
                    // can happen when the previous step did not trigger any message posted from the bot
                    // e.g: previous step was "forward_operator" and no-one is available
                    // -> in that case, don't wait and trigger the next step immediately
                    nextStepDelay = 0;
                } else {
                    this._chatbotSetIsTyping();
                }

                this.nextStepTimeout = setTimeout(
                    this._chatbotTriggerNextStep.bind(this), nextStepDelay);
            }
        }

        if (!this._chatbotDisplayRestartButton()) {
            this._chatWindow.$('.o_livechat_chatbot_main_restart').addClass('d-none');
        }
     },
     /**
      * See '_chatbotSaveSession'.
      *
      * We retrieve the livechat uuid from the session cookie since the livechat Widget is not yet
      * initialized when we restore the chatbot state.
      *
      * We also clear any older keys that store a previously saved chatbot session.
      * (In that case we clear the actual browser's local storage, we don't use the localStorage
      * object as it does not allow browsing existing keys, see 'local_storage.js'.)
      *
      * @private
      */
    _chatbotRestoreSession: function (sessionCookie) {
        const sessionKey = 'im_livechat.chatbot.state.uuid_' + JSON.parse(sessionCookie).uuid;
        const browserLocalStorage = window.localStorage;
        if (browserLocalStorage && browserLocalStorage.length) {
            for (let i = 0; i < browserLocalStorage.length; i++) {
                const key = browserLocalStorage.key(i);
                if (key.startsWith('im_livechat.chatbot.state.uuid_') && key !== sessionKey) {
                    browserLocalStorage.removeItem(key);
                }
            }
        }

        let chatbotState = localStorage.getItem(sessionKey);

        if (chatbotState) {
            chatbotState = JSON.parse(chatbotState);
            this._isChatbot = true;
            this._chatbot = chatbotState._chatbot;
            this._chatbotCurrentStep = chatbotState._chatbotCurrentStep;
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
    _chatbotSaveSession: function () {
        const chatUuid = this._livechat.toData().uuid;
        localStorage.setItem('im_livechat.chatbot.state.uuid_' + chatUuid, JSON.stringify({
            '_chatbot': this._chatbot,
            '_chatbotCurrentStep': this._chatbotCurrentStep,
        }));
    },
    /**
     * Adds a small "is typing" animation into the chat window.
     *
     * @private
     */
    _chatbotSetIsTyping: function (isWelcomeMessage=false) {
        if (this.isTypingTimeout) {
            clearTimeout(this.isTypingTimeout);
        }

        this._chatbotDisableInput('');

        this.isTypingTimeout = setTimeout(() => {
            this._chatWindow.$('.o_mail_thread_content').append(
                $(QWeb.render('im_livechat.legacy.chatbot.is_typing_message', {
                    'chatbotImageSrc': `/im_livechat/operator/${this._livechat.getOperatorPID()[0]}/avatar`,
                    'chatbotName': this._chatbot.chatbot_name,
                    'isWelcomeMessage': isWelcomeMessage,
                }))
            );

            this._chatWindow.scrollToBottom();
        }, this._chatbotMessageDelay / 3);
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
    _chatbotShouldEndScript: function () {
        if (this._chatbotCurrentStep.conversation_closed) {
            return true;
        }

        if (this._chatbotCurrentStep.chatbot_step_is_last &&
            (this._chatbotCurrentStep.chatbot_step_type !== 'forward_operator' ||
             !this._chatbotCurrentStep.chatbot_operator_found)) {
            if (this._chatbotCurrentStep.chatbot_step_type === 'question_email'
                && !this._chatbotCurrentStep.is_email_valid) {
                // email is not (yet) valid, let the user answer / try again
                return false;
            } else if ((this._chatbotIsExpectingUserInput() ||
                        this._chatbotCurrentStep.chatbot_step_type === 'question_selection') &&
                       this._messages.length !== 0) {
                const lastMessage = this._messages[this._messages.length - 1];
                if (lastMessage.getAuthorID() !== this._livechat.getOperatorPID()[0]) {
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
    _chatbotValidateEmail: async function () {
        let emailValidResult = await session.rpc('/chatbot/step/validate_email', {
            channel_uuid: this._livechat.getUUID(),
        });

        if (emailValidResult.success) {
            this._chatbotCurrentStep.is_email_valid = true;
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
    _chatbotTriggerNextStep: async function () {
        let triggerNextStep = true;
        if (this._chatbotCurrentStep && this._chatbotCurrentStep.chatbot_step_type === 'question_email') {
            triggerNextStep = await this._chatbotValidateEmail();
        }

        if (!triggerNextStep) {
            return;
        }

        const nextStep = await session.rpc('/chatbot/step/trigger', {
            channel_uuid: this._livechat.getUUID(),
            chatbot_script_id: this._chatbot.chatbot_script_id,
        });

        if (nextStep) {
            if (nextStep.chatbot_posted_message) {
                this._chatbotAddMessage(nextStep.chatbot_posted_message);
            }

            this._chatbotCurrentStep = nextStep.chatbot_step;

            this._chatbotProcessStep();
        } else {
            // did not find next step -> end the script
            this._chatbotCurrentStep['chatbot_step_is_last'] = true;
            this._renderMessages();
            this._chatbotEndScript();
        }

        this._chatbotSaveSession();

        return nextStep;
    },
    /**
     * Returns the 'this._messages' filtered on our special 'welcome' ones.
     * See '_sendWelcomeChatbotMessage'.
     *
     * @private
     */
    _getWelcomeMessages: function () {
        return this._messages.filter((message) => {
            return message._id && typeof message._id === 'string' && message._id.startsWith('_welcome_');
        });
    },
    /**
     * Compares the last message of the conversation to this livechat's operator id.
     *
     * @private
     */
    _isLastMessageFromCustomer: function () {
        const lastMessage = this._messages.length !== 0 ? this._messages[this._messages.length - 1] : null;
        return lastMessage && lastMessage.getAuthorID() !== this._livechat.getOperatorPID()[0];
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
     _askFeedback: function () {
        this._super(...arguments);

        if (this._chatbotCurrentStep) {
            this._chatbotCurrentStep.conversation_closed = true;
            this._chatbotSaveSession();
        }

        this._chatWindow.$('.o_livechat_chatbot_main_restart').addClass('d-none');
        this._chatWindow.$('.o_livechat_chatbot_end').hide();
        this._chatWindow.$('.o_composer_text_field')
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
    _openChatWindow: function () {
        return this._super(...arguments).then(() => {
            window.addEventListener('resize', () => {
                if (this._chatWindow) {
                    this._chatWindow.scrollToBottom();
                }
            });

            if (this._chatbotCurrentStep && this._messages && this._messages.length !== 0) {
                this._chatbotProcessStep();
            }
        });
    },
    /**
     * @private
     * @override
     */
    _prepareGetSessionParameters: function () {
        const parameters = this._super(...arguments);

        if (this._isChatbot) {
            parameters.chatbot_script_id = this._chatbot.chatbot_script_id;
        }

        return parameters;
    },
    /**
     * @private
     */
    _renderMessages: function () {
        this._super(...arguments);

        var self = this;

        this._chatWindow.$('.o_thread_message:last .o_livechat_chatbot_options li').each(function () {
            $(this).on('click', self._onChatbotOptionClicked.bind(self));
        });

        this._chatWindow.$('.o_livechat_chatbot_main_restart').on('click',
            this._onChatbotRestartScript.bind(this));

        if (this._messages.length !== 0) {
            const lastMessage = this._messages[this._messages.length - 1];
            const stepAnswers = lastMessage.getChatbotStepAnswers();
            if (stepAnswers && stepAnswers.length !== 0 && !lastMessage.getChatbotStepAnswerId()) {
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
    _sendMessage: async function (message) {
        const superArguments = arguments;
        const superMethod = this._super;

        if (this._livechat.isTemporary) {
            await this._createLivechatChannel();
            if (!this._livechat.getHasOperator()) {
                return;
            }
        }

        if (this._isChatbot && this._chatbotCurrentStep) {
            await this._chatbotPostWelcomeMessages();
        }

        return superMethod.apply(this, superArguments).then(() => {
            if (this._isChatbotRedirecting) {
                return;
            }

            if (this._isChatbot && this._chatbotCurrentStep) {
                if (this._chatbotCurrentStep.chatbot_step_type === 'forward_operator' &&
                    this._chatbotCurrentStep.chatbot_operator_found) {
                    return;  // operator has taken over the conversation, let them speak
                } else if (this._chatbotCurrentStep.chatbot_step_type === 'free_input_multi') {
                    this._debouncedChatbotAwaitUserInput();
                } else if (!this._chatbotShouldEndScript()) {
                    this._chatbotSetIsTyping();
                    this.nextStepTimeout = setTimeout(
                        this._chatbotTriggerNextStep.bind(this), this._chatbotMessageDelay);
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
    _sendWelcomeMessage: function () {
        if (this._isChatbot) {
            this._sendWelcomeChatbotMessage(
                0,
                this._chatbotBatchWelcomeMessages ? 0 : this._chatbotMessageDelay,
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
    _sendWelcomeChatbotMessage: function (stepIndex, welcomeMessageDelay) {
        const chatbotStep = this._chatbot.chatbot_welcome_steps[stepIndex];
        this._chatbotCurrentStep = chatbotStep;

        if (chatbotStep.chatbot_step_message) {
            this._addMessage({
                id: '_welcome_' + stepIndex,
                is_discussion: true,  // important for css style -> we only want white background for chatbot
                attachment_ids: [],
                author_id: this._livechat.getOperatorPID(),
                body: utils.Markup(chatbotStep.chatbot_step_message),
                chatbot_script_step_id: chatbotStep.chatbot_script_step_id,
                chatbot_step_answers: chatbotStep.chatbot_step_answers,
                date: time.datetime_to_str(new Date()),
                model: "mail.channel",
                message_type: "comment",
                res_id: this._livechat.getID(),
            });
        }

        if (stepIndex + 1 < this._chatbot.chatbot_welcome_steps.length) {
            if (welcomeMessageDelay !== 0) {
                this._chatbotSetIsTyping(true);
            }

            this.welcomeMessageTimeout = setTimeout(() => {
                this._sendWelcomeChatbotMessage(stepIndex + 1, welcomeMessageDelay);
                this._renderMessages();
            }, welcomeMessageDelay);
        } else {
            if (this._chatbotCurrentStep.chatbot_step_type === 'forward_operator') {
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
    _onChatbotRestartScript: async function (ev) {
        this._chatWindow.$('.o_composer_text_field').removeClass('d-none');
        this._chatWindow.$('.o_livechat_chatbot_end').hide();

        if (this.nextStepTimeout) {
            clearTimeout(this.nextStepTimeout);
        }

        if (this.welcomeMessageTimeout) {
            clearTimeout(this.welcomeMessageTimeout);
        }

        const postedMessage = await session.rpc('/chatbot/restart', {
            channel_uuid: this._livechat.getUUID(),
            chatbot_script_id: this._chatbot.chatbot_script_id,
        });

        if (postedMessage) {
            this._chatbotAddMessage(postedMessage);
        }

        this._chatbotCurrentStep = null;
        this._chatbotSetIsTyping();
        this.nextStepTimeout = setTimeout(
            this._chatbotTriggerNextStep.bind(this), this._chatbotMessageDelay);
    },

    _onChatbotInputKeyDown: function () {
        if (this._chatbotCurrentStep &&
            this._chatbotCurrentStep.chatbot_step_type === 'free_input_multi') {
            this._debouncedChatbotAwaitUserInput();
        }
    },

    /**
     * Saves the selected chatbot.script.answer onto our chatbot.message.
     * Will update the state of the related message (in this._messages) to set the selected option
     * as well which will in turn adapt the display to not show options anymore.
     *
     * This method also handles an optional redirection link placed on the chatbot.script.answer and
     * will make sure to properly save the selected choice before redirecting.
     *
     * @param {MouseEvent} ev
     * @private
     */
    _onChatbotOptionClicked: async function (ev) {
        ev.stopPropagation();

        const $target = $(ev.currentTarget);
        const stepId = $target.closest('ul').data('chatbotStepId');
        const selectedAnswer = $target.data('chatbotStepAnswerId');

        const redirectLink = $target.data('chatbotStepRedirectLink');
        this._isChatbotRedirecting = !!redirectLink;

        await this._sendMessage({
            content: $target.text().trim(),
        });

        let stepMessage = null;
        this._messages.forEach((message) => {
            // we do NOT want to use a 'find' here because we want the LAST message that respects
            // this condition.
            // indeed, if you restart the script, you can have multiple messages with the same step id,
            // but here we only care about the very last one (the current step of the script)
            // reversing the this.messages variable seems like a bad idea because it could have
            // bad implications for other flows (as the reverse is in-place, not in a copy)
            if (message.getChatbotStepId() === stepId) {
                stepMessage = message;
            }
        });
        const messageId = stepMessage.getID();
        stepMessage.setChatbotStepAnswerId(selectedAnswer);
        this._chatbotCurrentStep['chatbot_selected_answer_id'] = selectedAnswer;
        this._renderMessages();
        this._chatbotSaveSession();

        const saveAnswerPromise = session.rpc('/chatbot/answer/save', {
            channel_uuid: this._livechat.getUUID(),
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
