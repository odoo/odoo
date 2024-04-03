/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
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
});
