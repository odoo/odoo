/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Chatbot',
    recordMethods: {
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
                    this.messaging.publicLivechatGlobal.livechatButtonView.chatbotEndScript();
                } else {
                    this.messaging.publicLivechatGlobal.livechatButtonView.chatbotSetIsTyping();
                    this.messaging.publicLivechatGlobal.livechatButtonView.update({
                        chatbotNextStepTimeout: setTimeout(
                            this.messaging.publicLivechatGlobal.livechatButtonView.widget._chatbotTriggerNextStep.bind(this.messaging.publicLivechatGlobal.livechatButtonView.widget),
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
            if (this.messaging.publicLivechatGlobal.chatbotState === 'init') {
                return this.messaging.publicLivechatGlobal.rule.chatbot;
            }
            if (this.messaging.publicLivechatGlobal.chatbotState === 'welcome') {
                return this.messaging.publicLivechatGlobal.livechatInit.rule.chatbot;
            }
            if (
                this.messaging.publicLivechatGlobal.chatbotState === 'restore_session' &&
                this.messaging.publicLivechatGlobal.localStorageChatbotState
            ) {
                return this.messaging.publicLivechatGlobal.localStorageChatbotState._chatbot;
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
        lastWelcomeStep: attr({
            compute: '_computeLastWelcomeStep',
        }),
        name: attr({
            compute: '_computeName',
        }),
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
        shouldEndScript: attr({
            compute: '_computeShouldEndScript',
            default: false,
        }),
        welcomeSteps: attr({
            compute: '_computeWelcomeSteps',
        }),
    },
});
