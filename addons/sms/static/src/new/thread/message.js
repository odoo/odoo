/** @odoo-module */

import { Message } from "@mail/new/core_ui/message";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, "sms", {
    onClickFailure() {
        if (this.message.type === "sms") {
            this.env.services.action.doAction("sms.sms_resend_action", {
                additionalContext: {
                    default_mail_message_id: this.message.id,
                },
            });
        } else {
            this._super(...arguments);
        }
    },
});
