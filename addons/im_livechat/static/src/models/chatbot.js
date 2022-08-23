/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Chatbot',
    recordMethods: {
        /**
         * See 'chatbotSaveSession'.
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
                this.messaging.publicLivechatGlobal.chatbot.localStorageState
            ) {
                return this.messaging.publicLivechatGlobal.chatbot.localStorageState._chatbot;
            }
            return clear();
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
            if (this.messaging.publicLivechatGlobal.isWebsiteLivechatChatbotFlow) {
                return 100;
            }
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
            return 'im_livechat.chatbot.state.uuid_' + JSON.parse(!this.messaging.publicLivechatGlobal.sessionCookie).uuid;
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
        data: attr({
            compute: '_computeData',
        }),
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
        localStorageState: attr({
            compute: '_computeLocalStorageState',
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
        sessionCookieKey: attr({
            compute: '_computeSessionCookieKey',
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
