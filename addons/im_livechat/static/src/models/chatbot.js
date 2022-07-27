/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Chatbot',
    identifyingFields: ['livechatButtonViewOwner'],
    recordMethods: {
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
            if (this.livechatButtonViewOwner.isWebsiteLivechatChatbotFlow) {
                return 100;
            }
            return clear();
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeScriptId() {
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
            return this.data.chatbot_welcome_steps;
        },
    },
    fields: {
        data: attr(),
        currentStep: one('ChatbotStep', {
            inverse: 'chabotOwner',
            isCausal: true,
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
        livechatButtonViewOwner: one('LivechatButtonView', {
            inverse: 'chatbot',
            readonly: true,
            required: true,
        }),
        name: attr({
            compute: '_computeName',
        }),
        messageDelay: attr({
            compute: '_computeMessageDelay',
            default: 3500, // in milliseconds
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
