/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import { qweb } from 'web.core';

registerModel({
    name: 'Chatbot',
    recordMethods: {
        /**
         * Once the script ends, adds a visual element at the end of the chat window allowing to restart
         * the whole script.
         */
        endScript() {
            if (
                this.currentStep &&
                this.currentStep.data &&
                this.currentStep.data.conversation_closed
            ) {
                // don't touch anything if the user has closed the conversation, let the chat window
                // handle the display
                return;
            }
            this.messaging.publicLivechatGlobal.chatWindow.legacyChatWindow.$('.o_composer_text_field').addClass('d-none');
            this.messaging.publicLivechatGlobal.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_end').show();
            this.messaging.publicLivechatGlobal.chatWindow.legacyChatWindow.$('.o_livechat_chatbot_restart').one('click', this.messaging.publicLivechatGlobal.livechatButtonView.onChatbotRestartScript);
        },
        /**
         * See 'Chatbot/saveSession'.
         *
         * We retrieve the livechat uuid from the session cookie since the livechat Widget is not yet
         * initialized when we restore the chatbot state.
         *
         * We also clear any older keys that store a previously saved chatbot session.
         * (In that case we clear the actual browser's local storage, we don't use the localStorage
         * object as it does not allow browsing existing keys, see 'local_storage.js'.)
         */
        restoreSession() {
            const browserLocalStorage = window.localStorage;
            if (browserLocalStorage && browserLocalStorage.length) {
                for (let i = 0; i < browserLocalStorage.length; i++) {
                    const key = browserLocalStorage.key(i);
                    if (key.startsWith('im_livechat.chatbot.state.uuid_') && key !== this.sessionCookieKey) {
                        browserLocalStorage.removeItem(key);
                    }
                }
            }
            const chatbotState = localStorage.getItem(this.sessionCookieKey);
            if (chatbotState) {
                this.update({ currentStep: { data: this.localStorageState._chatbotCurrentStep } });
            }
        },
        /**
         * Register current chatbot step state into localStorage to be able to resume if the visitor
         * goes to another website page or if he refreshes his page.
         *
         * (Will not work if the visitor switches browser but his livechat session will not be restored
         *  anyway in that case, since it's stored into a cookie).
         */
        saveSession() {
            localStorage.setItem('im_livechat.chatbot.state.uuid_' + this.messaging.publicLivechatGlobal.publicLivechat.uuid, JSON.stringify({
                '_chatbot': this.data,
                '_chatbotCurrentStep': this.currentStep.data,
            }));
        },
        /**
         * Adds a small "is typing" animation into the chat window.
         *
         * @param {boolean} [isWelcomeMessage=false]
         */
        setIsTyping(isWelcomeMessage = false) {
            if (this.messaging.publicLivechatGlobal.livechatButtonView.isTypingTimeout) {
                clearTimeout(this.messaging.publicLivechatGlobal.livechatButtonView.isTypingTimeout);
            }
            this.messaging.publicLivechatGlobal.livechatButtonView.widget._chatbotDisableInput('');
            this.messaging.publicLivechatGlobal.livechatButtonView.update({
                isTypingTimeout: setTimeout(
                    () => {
                        this.messaging.publicLivechatGlobal.chatWindow.legacyChatWindow.$('.o_mail_thread_content').append(
                            $(qweb.render('im_livechat.legacy.chatbot.is_typing_message', {
                                'chatbotImageSrc': `/im_livechat/operator/${
                                    this.messaging.publicLivechatGlobal.publicLivechat.operator.id
                                }/avatar`,
                                'chatbotName': this.name,
                                'isWelcomeMessage': isWelcomeMessage,
                            }))
                        );
                        this.messaging.publicLivechatGlobal.chatWindow.publicLivechatView.widget.scrollToBottom();
                    },
                    this.messageDelay / 3,
                ),
            });
        },
        /**
         * Triggers the next step of the script by calling the associated route.
         * This will receive the next step and call step processing.
         */
        async triggerNextStep() {
            let triggerNextStep = true;
            if (
                this.currentStep &&
                this.currentStep.data &&
                this.currentStep.data.chatbot_step_type === 'question_email'
            ) {
                triggerNextStep = await this.messaging.publicLivechatGlobal.livechatButtonView.widget._chatbotValidateEmail();
            }

            if (!triggerNextStep) {
                return;
            }

            const nextStep = await this.messaging.rpc({
                route: '/chatbot/step/trigger',
                params: {
                    channel_uuid: this.messaging.publicLivechatGlobal.publicLivechat.uuid,
                    chatbot_script_id: this.scriptId,
                },
            });

            if (nextStep) {
                if (nextStep.chatbot_posted_message) {
                    this.messaging.publicLivechatGlobal.livechatButtonView.widget._chatbotAddMessage(nextStep.chatbot_posted_message);
                }

                this.update({ currentStep: { data: nextStep.chatbot_step } });

                this.messaging.publicLivechatGlobal.livechatButtonView.widget._chatbotProcessStep();
            } else {
                // did not find next step -> end the script
                this.currentStep.data.chatbot_step_is_last = true;
                this.messaging.publicLivechatGlobal.livechatButtonView.widget._renderMessages();
                this.endScript();
            }

            this.saveSession();

            return nextStep;
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
        awaitUserInput() {
            if (this.messaging.publicLivechatGlobal.isLastMessageFromCustomer) {
                if (this.shouldEndScript) {
                    this.endScript();
                } else {
                    this.setIsTyping();
                    this.update({
                        nextStepTimeout: setTimeout(
                            this.triggerNextStep,
                            this.messageDelay,
                        )
                    });
                }
            }
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeAwaitUserInputDebounceTime() {
            return 10000;
        },
        /**
         * @private
         * @returns {Object|FieldCommand}
         */
        _computeData() {
            if (this.messaging.publicLivechatGlobal.isTestChatbot) {
                return this.messaging.publicLivechatGlobal.testChatbotData.chatbot;
            }
            if (this.state === 'init') {
                return this.messaging.publicLivechatGlobal.rule.chatbot;
            }
            if (this.state === 'welcome') {
                return this.messaging.publicLivechatGlobal.livechatInit.rule.chatbot;
            }
            if (
                this.state === 'restore_session' &&
                this.localStorageState
            ) {
                return this.localStorageState._chatbot;
            }
            return clear();
        },
        /**
         * @private
         * @returns {function}
         */
        _computeDebouncedAwaitUserInput() {
            // debounced to let the user type several sentences, see 'Chatbot/awaitUserInput' for details
            return _.debounce(
                this.awaitUserInput,
                this.awaitUserInputDebounceTime,
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsExpectingUserInput() {
            if (!this.currentStep) {
                return clear();
            }
            return [
                'question_phone',
                'question_email',
                'free_input_single',
                'free_input_multi',
            ].includes(this.currentStep.data.chatbot_step_type);
        },
        /**
         * @private
         * @returns {FieldCommand|Object}
         */
        _computeLocalStorageState() {
            if (!this.messaging.publicLivechatGlobal.sessionCookie) {
                return clear();
            }
            const data = localStorage.getItem(this.sessionCookieKey);
            if (!data) {
                return clear();
            }
            return JSON.parse(data);
        },
        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            if (!this.data) {
                return clear();
            }
            return this.data.name;
        },
        /**
         * Will display a "Restart script" button in the conversation toolbar.
         *
         * Side-case: if the conversation has been forwarded to a human operator, we don't want to
         * display that restart button.
         *
         * @private
         * @returns {boolean}
         */
        _computeHasRestartButton() {
            return Boolean(
                !this.currentStep ||
                (
                    this.currentStep.data.chatbot_step_type !== 'forward_operator' ||
                    !this.currentStep.data.chatbot_operator_found
                )
            );
        },
        /**
         * @private
         * @returns {Array|FieldCommand}
         */
        _computeLastWelcomeStep() {
            if (!this.welcomeSteps) {
                return clear();
            }
            return this.welcomeSteps[this.welcomeSteps.length - 1];
        },
        /**
         * @private
         * @returns {integer|FieldCommand}
         */
        _computeMessageDelay() {
            return clear();
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeScriptId() {
            if (!this.data) {
                return clear();
            }
            return this.data.chatbot_script_id;
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeSessionCookieKey() {
            if (!this.messaging.publicLivechatGlobal.sessionCookie) {
                return clear();
            }
            return 'im_livechat.chatbot.state.uuid_' + JSON.parse(this.messaging.publicLivechatGlobal.sessionCookie).uuid;
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
         * @private
         * @returns {boolean}
         */
        _computeShouldEndScript() {
            if (!this.currentStep) {
                return clear();
            }
            if (this.currentStep.data.conversation_closed) {
                return true;
            }
            if (this.currentStep.data.chatbot_step_is_last &&
                (this.currentStep.data.chatbot_step_type !== 'forward_operator' ||
                !this.currentStep.data.chatbot_operator_found)
            ) {
                if (this.currentStep.data.chatbot_step_type === 'question_email'
                    && !this.currentStep.data.is_email_valid
                ) {
                    // email is not (yet) valid, let the user answer / try again
                    return false;
                } else if (
                    (this.isExpectingUserInput ||
                    this.currentStep.data.chatbot_step_type === 'question_selection') &&
                    this.messaging.publicLivechatGlobal.messages.length !== 0
                ) {
                    if (this.messaging.publicLivechatGlobal.lastMessage.authorId !== this.messaging.publicLivechatGlobal.publicLivechat.operator.id) {
                        // we are on the last step of the script, expect a user input and the user has
                        // already answered
                        // -> end the script
                        return true;
                    }
                } else if (!this.isExpectingUserInput) {
                    // we are on the last step of the script and we do not expect a user input
                    // -> end the script
                    return true;
                }
            }
            return false;
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeState() {
            if (this.messaging.publicLivechatGlobal.rule && !!this.messaging.publicLivechatGlobal.rule.chatbot) {
                return 'init';
            }
            if (this.messaging.publicLivechatGlobal.livechatInit && this.messaging.publicLivechatGlobal.livechatInit.rule.chatbot) {
                return 'welcome';
            }
            if (
                !this.messaging.publicLivechatGlobal.rule && 
                this.messaging.publicLivechatGlobal.history !== null &&
                this.messaging.publicLivechatGlobal.history.length !== 0 &&
                this.sessionCookieKey &&
                localStorage.getItem(this.sessionCookieKey)
            ) {
                return 'restore_session';
            }
            return clear();
        },
        /**
         * @private
         * @returns {Array|FieldCommand}
         */
        _computeWelcomeSteps() {
            if (!this.data) {
                return clear();
            }
            return this.data.chatbot_welcome_steps;
        },
    },
    fields: {
        awaitUserInputDebounceTime: attr({
            compute: '_computeAwaitUserInputDebounceTime',
        }),
        data: attr({
            compute: '_computeData',
        }),
        currentStep: one('ChatbotStep', {
            inverse: 'chabotOwner',
            isCausal: true,
        }),
        debouncedAwaitUserInput: attr({
            compute: '_computeDebouncedAwaitUserInput',
        }),
        hasRestartButton: attr({
            compute: '_computeHasRestartButton',
            default: false,
        }),
        isExpectingUserInput: attr({
            compute: '_computeIsExpectingUserInput',
            default: false,
        }),
        isRedirecting: attr({
            default: false,
        }),
        lastWelcomeStep: attr({
            compute: '_computeLastWelcomeStep',
        }),
        localStorageState: attr({
            compute: '_computeLocalStorageState',
        }),
        name: attr({
            compute: '_computeName',
        }),
        nextStepTimeout: attr(),
        messageDelay: attr({
            compute: '_computeMessageDelay',
            default: 3500, // in milliseconds
        }),
        publicLivechatGlobalOwner: one('PublicLivechatGlobal', {
            identifying: true,
            inverse: 'chatbot',
        }),
        scriptId: attr({
            compute: '_computeScriptId',
        }),
        serverUrl: attr(),
        sessionCookieKey: attr({
            compute: '_computeSessionCookieKey',
        }),
        shouldEndScript: attr({
            compute: '_computeShouldEndScript',
            default: false,
        }),
        state: attr({
            compute: '_computeState',
        }),
        welcomeMessageTimeout: attr(),
        welcomeSteps: attr({
            compute: '_computeWelcomeSteps',
        }),
    },
});
