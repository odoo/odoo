import { Message } from "@mail/next/models/message";
import { smsMessageFields } from "./sms_message_fields.generated";

/** @import { Extension } from "@web/next/store/model" */

export class SmsMessage extends /** @type {Extension<typeof Message, typeof smsMessageFields>} */ (
    Message
) {
    static _inherit = "mail.message";
    static fields = smsMessageFields;

    /** A message that failed to be delivered, by email or by sms. */
    get hasDeliveryError() {
        return this.has_error() || this.has_sms_error();
    }

    get isSms() {
        return this.message_type() === "sms";
    }
}
