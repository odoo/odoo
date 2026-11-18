import { Message } from "@mail/next/models/message";
import { smsMessageFields } from "./sms_message_fields.generated";

/** @import { Extension } from "@web/next/model/model" */

export class SmsMessage extends /** @type {Extension<typeof Message, typeof smsMessageFields>} */ (Message) {
    static _inherit = "mail.message";
    static fields = smsMessageFields;
}
