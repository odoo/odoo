/** @odoo-module **/

import {
    registerInstancePatchModel,
} from '@mail/model/model_core';

registerInstancePatchModel('mail.message', 'sms/static/src/models/message/message.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    openResendAction() {
        if (this.message_type === 'sms') {
            this.env.bus.trigger('do-action', {
                action: 'sms.sms_resend_action',
                options: {
                    additional_context: {
                        default_mail_message_id: this.id,
                    },
                },
            });
        } else {
            this._super(...arguments);
        }
    },
});
