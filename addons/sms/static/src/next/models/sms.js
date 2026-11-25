import { Model } from "@web/next/store/model";
import { smsSmsFields } from "./sms_fields.generated";

/** @extends {Model<typeof smsSmsFields>} */
export class Sms extends Model {
    static _name = "sms.sms";
    static fields = smsSmsFields;

    get isFailed() {
        return this.state() === "error";
    }

    /** Who the sms is for: the name of the customer, or the number. */
    get recipientName() {
        return this.partner_id()?.label() || this.number() || "";
    }

    /** Whether the customer could have been reached by email instead. */
    get hasEmailFallback() {
        return Boolean(this.partner_id()?.canBeEmailed);
    }

    cancel() {
        if (this.state() !== "outgoing") {
            throw new Error(`The sms to ${this.recipientName} was already sent`);
        }
        this.state.set("canceled");
        this.mail_message_id()?.has_sms_error.set(false);
    }
}
