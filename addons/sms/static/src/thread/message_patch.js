/** @odoo-module */

import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    onClickFailure() {
        if (this.message.type === "sms") {
            this.env.services.action.doAction("sms.sms_resend_action", {
                additionalContext: {
                    default_mail_message_id: this.message.id,
                },
            });
        } else {
            super.onClickFailure(...arguments);
        }
    },
});
