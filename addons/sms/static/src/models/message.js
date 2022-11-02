/** @odoo-module **/

import { Patch } from '@mail/model';
import { clear } from '@mail/model/model_field_command';

Patch({
    name: 'Message',
    recordMethods: {
        /**
         * @override
         */
        openResendAction() {
            if (this.message_type === 'sms') {
                this.env.services.action.doAction(
                    'sms.sms_resend_action',
                    {
                        additionalContext: {
                            default_mail_message_id: this.id,
                        },
                    },
                );
            } else {
                this._super(...arguments);
            }
        },
    },
    fields: {
        hasTextMuted: {
            compute() {
                if (this.message_type !== 'sms') {
                    return clear();
                }
                return this._super();
            }
        },
        isDisplayedInChatBubble: {
            compute() {
                if (this.message_type === 'sms') {
                    return true;
                }
                return this._super();
            },
        },
    },
});
