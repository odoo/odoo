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
         * @returns {string}
         */
        _computeName() {
            return this.data.name;
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
        welcomeSteps: attr({
            compute: '_computeWelcomeSteps',
        }),
    },
});
