/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'Message',
    recordMethods: {
        /**
         * Cancels the 'snailmail.letter' corresponding to this message.
         *
         * @returns {Deferred}
         */
        async cancelLetter() {
            // the result will come from the bus: message_notification_update
            await this.messaging.rpc({
                model: 'mail.message',
                method: 'cancel_letter',
                args: [[this.id]],
            });
        },
        /**
         * Opens the action about 'snailmail.letter' format error.
         */
        openFormatLetterAction() {
            this.env.services.action.doAction(
                'snailmail.snailmail_letter_format_error_action',
                {
                    additionalContext: {
                        message_id: this.id,
                    },
                },
            );
        },
        /**
         * Opens the action about 'snailmail.letter' missing fields.
         */
        async openMissingFieldsLetterAction() {
            const letterIds = await this.messaging.rpc({
                model: 'snailmail.letter',
                method: 'search',
                args: [[['message_id', '=', this.id]]],
            });
            this.env.services.action.doAction(
                'snailmail.snailmail_letter_missing_required_fields_action',
                {
                    additionalContext: {
                        default_letter_id: letterIds[0],
                    },
                }
            );
        },
        /**
         * Retries to send the 'snailmail.letter' corresponding to this message.
         */
        async resendLetter() {
            // the result will come from the bus: message_notification_update
            await this.messaging.rpc({
                model: 'mail.message',
                method: 'send_letter',
                args: [[this.id]],
            });
        },
    },
});
