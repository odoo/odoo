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
         * @returns {Object|FieldCommand}
         */
        _computeLastWelcomeStep() {
            if (!this.welcomeSteps) {
                return clear();
            }
            return this.welcomeSteps[this.welcomeSteps.length - 1];
        },
        /**
         * @private
         * @returns {Array|FieldCommand}
         */
        _computeWelcomeSteps() {
            if (this.data) {
                return this.data.chatbot_welcome_steps;
            }
            return clear();
        },
    },
    fields: {
        data: attr(),
        lastWelcomeStep: attr({
            compute: '_computeLastWelcomeStep',
        }),
        livechatButtonViewOwner: one('LivechatButtonView', {
            inverse: 'chatbot',
            readonly: true,
            required: true,
        }),
        welcomeSteps: attr({
            compute: '_computeWelcomeSteps',
        }),
    },
});
