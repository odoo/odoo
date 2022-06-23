/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/message';

patchRecordMethods('Message', {
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
});
